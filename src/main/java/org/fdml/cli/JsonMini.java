package org.fdml.cli;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class JsonMini {

  private JsonMini() {}

  static Object parse(String json) {
    return new Parser(json == null ? "" : json).parse();
  }

  private static final class Parser {
    private final String s;
    private int i = 0;

    Parser(String s) {
      this.s = s;
    }

    Object parse() {
      skipWs();
      Object v = parseValue();
      skipWs();
      if (i != s.length()) throw new IllegalArgumentException("trailing characters at index " + i);
      return v;
    }

    private Object parseValue() {
      skipWs();
      if (i >= s.length()) throw new IllegalArgumentException("unexpected end of input");
      char c = s.charAt(i);
      if (c == '{') return parseObject();
      if (c == '[') return parseArray();
      if (c == '"') return parseString();
      if (c == 't') return parseTrue();
      if (c == 'f') return parseFalse();
      if (c == 'n') return parseNull();
      if (c == '-' || (c >= '0' && c <= '9')) return parseNumber();
      throw new IllegalArgumentException("unexpected token '" + c + "' at index " + i);
    }

    private Map<String, Object> parseObject() {
      expect('{');
      skipWs();
      Map<String, Object> out = new LinkedHashMap<>();
      if (peek('}')) {
        i++;
        return out;
      }
      while (true) {
        skipWs();
        String key = parseString();
        skipWs();
        expect(':');
        Object val = parseValue();
        out.put(key, val);
        skipWs();
        if (peek('}')) {
          i++;
          return out;
        }
        expect(',');
      }
    }

    private List<Object> parseArray() {
      expect('[');
      skipWs();
      List<Object> out = new ArrayList<>();
      if (peek(']')) {
        i++;
        return out;
      }
      while (true) {
        out.add(parseValue());
        skipWs();
        if (peek(']')) {
          i++;
          return out;
        }
        expect(',');
      }
    }

    private String parseString() {
      expect('"');
      StringBuilder sb = new StringBuilder();
      while (i < s.length()) {
        char c = s.charAt(i++);
        if (c == '"') return sb.toString();
        if (c != '\\') {
          sb.append(c);
          continue;
        }
        if (i >= s.length()) throw new IllegalArgumentException("unterminated escape at index " + i);
        char e = s.charAt(i++);
        switch (e) {
          case '"': sb.append('"'); break;
          case '\\': sb.append('\\'); break;
          case '/': sb.append('/'); break;
          case 'b': sb.append('\b'); break;
          case 'f': sb.append('\f'); break;
          case 'n': sb.append('\n'); break;
          case 'r': sb.append('\r'); break;
          case 't': sb.append('\t'); break;
          case 'u': {
            if (i + 4 > s.length()) throw new IllegalArgumentException("bad unicode escape at index " + i);
            String hex = s.substring(i, i + 4);
            try {
              sb.append((char) Integer.parseInt(hex, 16));
            } catch (NumberFormatException nfe) {
              throw new IllegalArgumentException("bad unicode escape: " + hex + " at index " + i);
            }
            i += 4;
            break;
          }
          default:
            throw new IllegalArgumentException("bad escape '\\" + e + "' at index " + (i - 1));
        }
      }
      throw new IllegalArgumentException("unterminated string");
    }

    private Boolean parseTrue() {
      expectWord("true");
      return Boolean.TRUE;
    }

    private Boolean parseFalse() {
      expectWord("false");
      return Boolean.FALSE;
    }

    private Object parseNull() {
      expectWord("null");
      return null;
    }

    private Number parseNumber() {
      int start = i;
      if (peek('-')) i++;
      if (peek('0')) {
        i++;
      } else {
        if (!isDigit(peekChar())) throw new IllegalArgumentException("bad number at index " + i);
        while (isDigit(peekChar())) i++;
      }
      boolean isFloat = false;
      if (peek('.')) {
        isFloat = true;
        i++;
        if (!isDigit(peekChar())) throw new IllegalArgumentException("bad number fraction at index " + i);
        while (isDigit(peekChar())) i++;
      }
      char c = peekChar();
      if (c == 'e' || c == 'E') {
        isFloat = true;
        i++;
        c = peekChar();
        if (c == '+' || c == '-') i++;
        if (!isDigit(peekChar())) throw new IllegalArgumentException("bad number exponent at index " + i);
        while (isDigit(peekChar())) i++;
      }
      String n = s.substring(start, i);
      try {
        if (isFloat) return Double.parseDouble(n);
        return Long.parseLong(n);
      } catch (NumberFormatException nfe) {
        throw new IllegalArgumentException("bad number: " + n);
      }
    }

    private void skipWs() {
      while (i < s.length()) {
        char c = s.charAt(i);
        if (c == ' ' || c == '\n' || c == '\r' || c == '\t') i++;
        else break;
      }
    }

    private void expect(char c) {
      if (i >= s.length() || s.charAt(i) != c) {
        throw new IllegalArgumentException("expected '" + c + "' at index " + i);
      }
      i++;
    }

    private void expectWord(String w) {
      if (i + w.length() > s.length() || !s.substring(i, i + w.length()).equals(w)) {
        throw new IllegalArgumentException("expected '" + w + "' at index " + i);
      }
      i += w.length();
    }

    private boolean peek(char c) {
      return i < s.length() && s.charAt(i) == c;
    }

    private char peekChar() {
      return i < s.length() ? s.charAt(i) : '\0';
    }

    private boolean isDigit(char c) {
      return c >= '0' && c <= '9';
    }
  }
}
