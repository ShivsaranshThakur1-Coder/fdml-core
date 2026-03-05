package org.fdml.cli;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class Enrichment {
  private static final String DEFAULT_ENV_FILE = ".env";
  private static final int DEFAULT_TIMEOUT_SECONDS = 15;
  private static final int MAX_GROQ_PROMPT_CHARS = 4000;
  private static final int MAX_STEP_LEN = 80;
  private static final Pattern URL_PATTERN = Pattern.compile("https?://\\S+", Pattern.CASE_INSENSITIVE);
  private static final Pattern YT_ID_SHORT = Pattern.compile("youtu\\.be/([A-Za-z0-9_-]{11})");
  private static final Pattern YT_ID_WATCH = Pattern.compile("[?&]v=([A-Za-z0-9_-]{11})");
  private static final Pattern IMAGE_URL = Pattern.compile("(?i).+\\.(png|jpe?g|webp|bmp|tiff?)$");

  private Enrichment() {}

  static final class Result {
    final boolean enabled;
    final boolean offline;
    final String envFile;
    final String effectiveText;
    final boolean effectiveTextChanged;
    final List<String> suggestedSteps;
    final List<String> notes;
    final List<ProviderStatus> providers;

    Result(boolean enabled,
           boolean offline,
           String envFile,
           String effectiveText,
           boolean effectiveTextChanged,
           List<String> suggestedSteps,
           List<String> notes,
           List<ProviderStatus> providers) {
      this.enabled = enabled;
      this.offline = offline;
      this.envFile = envFile;
      this.effectiveText = effectiveText;
      this.effectiveTextChanged = effectiveTextChanged;
      this.suggestedSteps = List.copyOf(suggestedSteps);
      this.notes = List.copyOf(notes);
      this.providers = List.copyOf(providers);
    }

    String toReportJson(String sourcePath) {
      StringBuilder sb = new StringBuilder();
      sb.append("{");
      sb.append("\"schemaVersion\":\"1\",");
      sb.append("\"sourcePath\":\"").append(jsonEscape(sourcePath == null ? "" : sourcePath)).append("\",");
      sb.append("\"enabled\":").append(enabled).append(",");
      sb.append("\"offline\":").append(offline).append(",");
      sb.append("\"envFile\":\"").append(jsonEscape(envFile)).append("\",");
      sb.append("\"effectiveTextChanged\":").append(effectiveTextChanged).append(",");
      sb.append("\"suggestedStepsCount\":").append(suggestedSteps.size()).append(",");
      sb.append("\"notes\":[");
      for (int i = 0; i < notes.size(); i++) {
        if (i > 0) sb.append(",");
        sb.append("\"").append(jsonEscape(notes.get(i))).append("\"");
      }
      sb.append("],");
      sb.append("\"providers\":[");
      for (int i = 0; i < providers.size(); i++) {
        ProviderStatus p = providers.get(i);
        if (i > 0) sb.append(",");
        sb.append("{");
        sb.append("\"name\":\"").append(jsonEscape(p.name)).append("\",");
        sb.append("\"configured\":").append(p.configured).append(",");
        sb.append("\"attempted\":").append(p.attempted).append(",");
        sb.append("\"applied\":").append(p.applied).append(",");
        sb.append("\"status\":\"").append(jsonEscape(p.status)).append("\",");
        sb.append("\"detail\":\"").append(jsonEscape(p.detail)).append("\"");
        sb.append("}");
      }
      sb.append("]}");
      return sb.toString();
    }
  }

  private static final class ProviderStatus {
    final String name;
    final String keyName;
    final boolean configured;
    boolean attempted;
    boolean applied;
    String status;
    String detail;

    ProviderStatus(String name, String keyName, boolean configured) {
      this.name = name;
      this.keyName = keyName;
      this.configured = configured;
      this.attempted = false;
      this.applied = false;
      this.status = "skipped";
      this.detail = configured ? "not_attempted" : "missing_api_key";
    }
  }

  static Result apply(String sourceText, String envFilePath, boolean enabled) {
    String envFile = envFilePath == null || envFilePath.isBlank() ? DEFAULT_ENV_FILE : envFilePath;
    Map<String, String> env = resolveEnv(envFile);
    boolean offline = truthy(env.getOrDefault("FDML_OFFLINE", ""));

    List<ProviderStatus> providers = providerDefaults(env);
    Map<String, ProviderStatus> byName = new HashMap<>();
    for (ProviderStatus p : providers) byName.put(p.name, p);

    if (!enabled) {
      for (ProviderStatus p : providers) {
        p.status = "disabled";
        p.detail = "enrichment_disabled";
      }
      return new Result(false, offline, envFile, sourceText, false, List.of(), List.of(), providers);
    }

    if (offline) {
      for (ProviderStatus p : providers) {
        p.status = "skipped";
        p.detail = "offline_mode";
      }
      return new Result(true, true, envFile, sourceText, false, List.of(), List.of(), providers);
    }

    HttpClient http = HttpClient.newBuilder()
      .connectTimeout(Duration.ofSeconds(DEFAULT_TIMEOUT_SECONDS))
      .build();
    int timeoutSeconds = parsePositiveInt(env.get("FDML_ENRICH_TIMEOUT_S"), DEFAULT_TIMEOUT_SECONDS);
    String userAgent = env.getOrDefault(
      "FDML_HTTP_USER_AGENT",
      "fdml-core-ingest/1.0 (+https://github.com/ShivsaranshThakur1-Coder/fdml-core)"
    );

    String effectiveText = sourceText;
    List<String> notes = new ArrayList<>();

    ProviderStatus ocr = byName.get("ocr_space");
    if (!ocr.configured) {
      ocr.status = "skipped";
      ocr.detail = "missing_api_key";
    } else {
      List<String> imageUrls = extractImageUrls(sourceText);
      if (imageUrls.isEmpty()) {
        ocr.status = "skipped";
        ocr.detail = "no_image_url_in_source";
      } else {
        ocr.attempted = true;
        String ocrText = tryOcrFromImageUrls(http, imageUrls, trim(env.get(ocr.keyName)), timeoutSeconds, userAgent);
        if (!ocrText.isBlank()) {
          effectiveText = effectiveText + "\n" + ocrText;
          notes.add("OCR appended text from image URL");
          ocr.applied = true;
          ocr.status = "ok";
          ocr.detail = "appended_text";
        } else {
          ocr.status = "ok";
          ocr.detail = "no_text_extracted";
        }
      }
    }

    ProviderStatus deepl = byName.get("deepl");
    if (!deepl.configured) {
      deepl.status = "skipped";
      deepl.detail = "missing_api_key";
    } else if (!looksNonAsciiHeavy(effectiveText)) {
      deepl.status = "skipped";
      deepl.detail = "text_already_ascii";
    } else {
      deepl.attempted = true;
      String translated = tryDeeplTranslateToEnglish(http, effectiveText, trim(env.get(deepl.keyName)), timeoutSeconds, userAgent);
      if (!translated.isBlank()) {
        effectiveText = translated;
        notes.add("DeepL translated source to English");
        deepl.applied = true;
        deepl.status = "ok";
        deepl.detail = "translated_to_en";
      } else {
        deepl.status = "ok";
        deepl.detail = "no_translation_returned";
      }
    }

    ProviderStatus youtube = byName.get("youtube");
    if (!youtube.configured) {
      youtube.status = "skipped";
      youtube.detail = "missing_api_key";
    } else {
      LinkedHashSet<String> ids = extractYouTubeIds(sourceText, 2);
      if (ids.isEmpty()) {
        youtube.status = "skipped";
        youtube.detail = "no_youtube_url_in_source";
      } else {
        youtube.attempted = true;
        List<String> ytTitles = tryYouTubeTitles(http, ids, trim(env.get(youtube.keyName)), timeoutSeconds, userAgent);
        if (!ytTitles.isEmpty()) {
          notes.add("YouTube metadata: " + String.join(" | ", ytTitles));
          youtube.applied = true;
          youtube.status = "ok";
          youtube.detail = "metadata_collected";
        } else {
          youtube.status = "ok";
          youtube.detail = "no_metadata_returned";
        }
      }
    }

    List<String> suggestedSteps = List.of();
    ProviderStatus groq = byName.get("groq");
    if (!groq.configured) {
      groq.status = "skipped";
      groq.detail = "missing_api_key";
    } else {
      groq.attempted = true;
      List<String> fromGroq = tryGroqStepNormalization(http, effectiveText, trim(env.get(groq.keyName)), timeoutSeconds, userAgent);
      if (!fromGroq.isEmpty()) {
        suggestedSteps = fromGroq;
        notes.add("Groq normalized " + fromGroq.size() + " step(s)");
        groq.applied = true;
        groq.status = "ok";
        groq.detail = "suggestions_applied";
      } else {
        groq.status = "ok";
        groq.detail = "no_suggestions";
      }
    }

    return new Result(
      true,
      false,
      envFile,
      effectiveText,
      !effectiveText.equals(sourceText),
      suggestedSteps,
      notes,
      providers
    );
  }

  private static List<ProviderStatus> providerDefaults(Map<String, String> env) {
    List<ProviderStatus> out = new ArrayList<>();
    out.add(new ProviderStatus("groq", "GROQ_API_KEY", !trim(env.get("GROQ_API_KEY")).isEmpty()));
    out.add(new ProviderStatus("ocr_space", "OCR_SPACE_API_KEY", !trim(env.get("OCR_SPACE_API_KEY")).isEmpty()));
    out.add(new ProviderStatus("deepl", "DEEPL_API_KEY", !trim(env.get("DEEPL_API_KEY")).isEmpty()));
    out.add(new ProviderStatus("youtube", "YOUTUBE_API_KEY", !trim(env.get("YOUTUBE_API_KEY")).isEmpty()));
    return out;
  }

  private static Map<String, String> resolveEnv(String envFilePath) {
    Map<String, String> out = new HashMap<>(System.getenv());
    Path envFile = Path.of(envFilePath == null || envFilePath.isBlank() ? DEFAULT_ENV_FILE : envFilePath);
    if (Files.exists(envFile)) {
      try {
        for (String raw : Files.readAllLines(envFile, StandardCharsets.UTF_8)) {
          String line = raw.trim();
          if (line.isEmpty() || line.startsWith("#")) continue;
          int eq = line.indexOf('=');
          if (eq <= 0) continue;
          String key = line.substring(0, eq).trim();
          String value = line.substring(eq + 1).trim();
          out.put(key, value);
        }
      } catch (Exception ignored) {
        // Best-effort read only.
      }
    }
    return out;
  }

  private static String tryOcrFromImageUrls(HttpClient http,
                                            List<String> imageUrls,
                                            String apiKey,
                                            int timeoutSeconds,
                                            String userAgent) {
    for (String url : imageUrls) {
      String endpoint = "https://api.ocr.space/parse/imageurl?apikey="
        + urlEncode(apiKey)
        + "&url="
        + urlEncode(url);
      String body = get(http, endpoint, timeoutSeconds, userAgent, Map.of());
      if (body == null) continue;
      List<String> parsed = allJsonStringFields(body, "ParsedText");
      String joined = collapseWhitespace(String.join(" ", parsed));
      if (!joined.isBlank()) return joined;
    }
    return "";
  }

  private static String tryDeeplTranslateToEnglish(HttpClient http,
                                                   String text,
                                                   String apiKey,
                                                   int timeoutSeconds,
                                                   String userAgent) {
    String trimmed = text.length() > MAX_GROQ_PROMPT_CHARS ? text.substring(0, MAX_GROQ_PROMPT_CHARS) : text;
    String form = "target_lang=EN&preserve_formatting=1&text=" + urlEncode(trimmed);
    String body = postForm(
      http,
      "https://api-free.deepl.com/v2/translate",
      form,
      timeoutSeconds,
      userAgent,
      Map.of("Authorization", "DeepL-Auth-Key " + apiKey)
    );
    if (body == null) return "";
    String translated = firstJsonStringField(body, "text");
    return collapseWhitespace(translated);
  }

  private static List<String> tryYouTubeTitles(HttpClient http,
                                               LinkedHashSet<String> ids,
                                               String apiKey,
                                               int timeoutSeconds,
                                               String userAgent) {
    String endpoint = "https://www.googleapis.com/youtube/v3/videos?part=snippet&id="
      + urlEncode(String.join(",", ids))
      + "&key="
      + urlEncode(apiKey);
    String body = get(http, endpoint, timeoutSeconds, userAgent, Map.of());
    if (body == null) return List.of();

    List<String> titles = allJsonStringFields(body, "title");
    List<String> out = new ArrayList<>();
    for (String t : titles) {
      String norm = collapseWhitespace(t);
      if (!norm.isBlank()) out.add(norm);
      if (out.size() >= 2) break;
    }
    return out;
  }

  private static List<String> tryGroqStepNormalization(HttpClient http,
                                                       String text,
                                                       String apiKey,
                                                       int timeoutSeconds,
                                                       String userAgent) {
    String input = text.length() > MAX_GROQ_PROMPT_CHARS ? text.substring(0, MAX_GROQ_PROMPT_CHARS) : text;
    String prompt =
      "Convert the dance notes into concise action lines.\n"
      + "Return plain text lines only. No numbering. One line per step.\n"
      + "Maximum 32 lines. Maximum 80 characters per line.\n\n"
      + "Notes:\n"
      + input;

    String requestJson = "{"
      + "\"model\":\"llama-3.1-8b-instant\","
      + "\"temperature\":0,"
      + "\"max_tokens\":256,"
      + "\"messages\":["
      + "{\"role\":\"system\",\"content\":\"You normalize dance notes into short step actions.\"},"
      + "{\"role\":\"user\",\"content\":\"" + jsonEscape(prompt) + "\"}"
      + "]"
      + "}";
    String body = postJson(
      http,
      "https://api.groq.com/openai/v1/chat/completions",
      requestJson,
      timeoutSeconds,
      userAgent,
      Map.of("Authorization", "Bearer " + apiKey)
    );
    if (body == null) return List.of();
    String content = firstJsonStringField(body, "content");
    if (content.isBlank()) return List.of();

    LinkedHashSet<String> lines = new LinkedHashSet<>();
    for (String raw : content.split("\\R")) {
      String line = raw.replaceFirst("^\\s*(?:[-*]|\\d+[.)])\\s*", "").trim();
      line = collapseWhitespace(line);
      if (line.isBlank()) continue;
      if (line.length() > MAX_STEP_LEN) line = line.substring(0, MAX_STEP_LEN).trim();
      lines.add(line);
      if (lines.size() >= 32) break;
    }
    return new ArrayList<>(lines);
  }

  private static List<String> extractUrls(String text) {
    List<String> urls = new ArrayList<>();
    Matcher m = URL_PATTERN.matcher(text == null ? "" : text);
    while (m.find()) {
      String raw = m.group();
      if (raw == null) continue;
      String cleaned = raw.replaceAll("[),.;]+$", "");
      if (!cleaned.isBlank()) urls.add(cleaned);
    }
    return urls;
  }

  private static List<String> extractImageUrls(String text) {
    List<String> out = new ArrayList<>();
    for (String url : extractUrls(text)) if (IMAGE_URL.matcher(url).matches()) out.add(url);
    return out;
  }

  private static LinkedHashSet<String> extractYouTubeIds(String text, int limit) {
    LinkedHashSet<String> ids = new LinkedHashSet<>();
    for (String url : extractUrls(text)) {
      String id = extractYouTubeId(url);
      if (id.isBlank()) continue;
      ids.add(id);
      if (ids.size() >= limit) break;
    }
    return ids;
  }

  private static String extractYouTubeId(String url) {
    Matcher shortM = YT_ID_SHORT.matcher(url);
    if (shortM.find()) return shortM.group(1);
    Matcher watchM = YT_ID_WATCH.matcher(url);
    if (watchM.find()) return watchM.group(1);
    return "";
  }

  private static boolean looksNonAsciiHeavy(String text) {
    if (text == null || text.isBlank()) return false;
    int total = 0;
    int nonAscii = 0;
    for (int i = 0; i < text.length(); i++) {
      char c = text.charAt(i);
      if (Character.isWhitespace(c)) continue;
      total++;
      if (c > 127) nonAscii++;
    }
    if (total == 0) return false;
    double ratio = (double) nonAscii / (double) total;
    return ratio >= 0.10;
  }

  private static String get(HttpClient http,
                            String url,
                            int timeoutSeconds,
                            String userAgent,
                            Map<String, String> headers) {
    try {
      HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(url))
        .GET()
        .timeout(Duration.ofSeconds(timeoutSeconds))
        .header("User-Agent", userAgent)
        .header("Accept", "application/json,text/plain;q=0.9,*/*;q=0.1");
      for (Map.Entry<String, String> e : headers.entrySet()) b.header(e.getKey(), e.getValue());
      HttpResponse<String> r = http.send(b.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
      return r.statusCode() >= 200 && r.statusCode() < 300 ? r.body() : null;
    } catch (Exception e) {
      return null;
    }
  }

  private static String postForm(HttpClient http,
                                 String url,
                                 String formBody,
                                 int timeoutSeconds,
                                 String userAgent,
                                 Map<String, String> headers) {
    try {
      HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(url))
        .POST(HttpRequest.BodyPublishers.ofString(formBody, StandardCharsets.UTF_8))
        .timeout(Duration.ofSeconds(timeoutSeconds))
        .header("User-Agent", userAgent)
        .header("Accept", "application/json,text/plain;q=0.9,*/*;q=0.1")
        .header("Content-Type", "application/x-www-form-urlencoded");
      for (Map.Entry<String, String> e : headers.entrySet()) b.header(e.getKey(), e.getValue());
      HttpResponse<String> r = http.send(b.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
      return r.statusCode() >= 200 && r.statusCode() < 300 ? r.body() : null;
    } catch (Exception e) {
      return null;
    }
  }

  private static String postJson(HttpClient http,
                                 String url,
                                 String jsonBody,
                                 int timeoutSeconds,
                                 String userAgent,
                                 Map<String, String> headers) {
    try {
      HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(url))
        .POST(HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8))
        .timeout(Duration.ofSeconds(timeoutSeconds))
        .header("User-Agent", userAgent)
        .header("Accept", "application/json,text/plain;q=0.9,*/*;q=0.1")
        .header("Content-Type", "application/json");
      for (Map.Entry<String, String> e : headers.entrySet()) b.header(e.getKey(), e.getValue());
      HttpResponse<String> r = http.send(b.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
      return r.statusCode() >= 200 && r.statusCode() < 300 ? r.body() : null;
    } catch (Exception e) {
      return null;
    }
  }

  private static String firstJsonStringField(String json, String key) {
    if (json == null || key == null || key.isBlank()) return "";
    Pattern p = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"");
    Matcher m = p.matcher(json);
    if (!m.find()) return "";
    return jsonUnescape(m.group(1));
  }

  private static List<String> allJsonStringFields(String json, String key) {
    if (json == null || key == null || key.isBlank()) return List.of();
    Pattern p = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"");
    Matcher m = p.matcher(json);
    List<String> out = new ArrayList<>();
    while (m.find()) out.add(jsonUnescape(m.group(1)));
    return out;
  }

  private static String jsonUnescape(String s) {
    if (s == null || s.isEmpty()) return "";
    StringBuilder out = new StringBuilder(s.length());
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      if (c != '\\') {
        out.append(c);
        continue;
      }
      if (i + 1 >= s.length()) {
        out.append('\\');
        continue;
      }
      char n = s.charAt(++i);
      switch (n) {
        case '"': out.append('"'); break;
        case '\\': out.append('\\'); break;
        case '/': out.append('/'); break;
        case 'b': out.append('\b'); break;
        case 'f': out.append('\f'); break;
        case 'n': out.append('\n'); break;
        case 'r': out.append('\r'); break;
        case 't': out.append('\t'); break;
        case 'u': {
          if (i + 4 <= s.length() - 1) {
            String hex = s.substring(i + 1, i + 5);
            try {
              out.append((char) Integer.parseInt(hex, 16));
              i += 4;
            } catch (NumberFormatException e) {
              out.append("\\u").append(hex);
              i += 4;
            }
          } else {
            out.append("\\u");
          }
          break;
        }
        default:
          out.append(n);
      }
    }
    return out.toString();
  }

  private static String urlEncode(String v) {
    return URLEncoder.encode(v, StandardCharsets.UTF_8);
  }

  private static String trim(String s) {
    return s == null ? "" : s.trim();
  }

  private static boolean truthy(String s) {
    String v = trim(s).toLowerCase(Locale.ROOT);
    return "1".equals(v) || "true".equals(v) || "yes".equals(v) || "on".equals(v);
  }

  private static int parsePositiveInt(String s, int fallback) {
    try {
      int v = Integer.parseInt(trim(s));
      return v > 0 ? v : fallback;
    } catch (Exception e) {
      return fallback;
    }
  }

  private static String jsonEscape(String s) {
    if (s == null) return "";
    return s.replace("\\", "\\\\")
      .replace("\"", "\\\"")
      .replace("\n", "\\n")
      .replace("\r", "\\r")
      .replace("\t", "\\t");
  }

  private static String collapseWhitespace(String s) {
    if (s == null) return "";
    return s.replaceAll("\\s+", " ").trim();
  }
}
