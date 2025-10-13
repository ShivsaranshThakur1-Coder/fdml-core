package org.fdml.cli;

class MainJson {
  static String esc(String s){ if(s==null)return null; return s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r",""); }

  static String toJsonDoctor(java.util.List<FdmlValidator.Result> rX,
                             java.util.List<SchematronValidator.Result> rS,
                             java.util.List<Linter.FileResult> rL){
    StringBuilder sb=new StringBuilder();
    sb.append("{\"command\":\"doctor\",\"xsd\":[");
    for(int i=0;i<rX.size();i++){ var r=rX.get(i);
      sb.append("{\"file\":\"").append(esc(r.file.toString())).append("\",\"ok\":").append(r.ok);
      if(!r.ok && r.message!=null) sb.append(",\"error\":\"").append(esc(r.message)).append("\"");
      sb.append("}"); if(i<rX.size()-1) sb.append(",");
    }
    sb.append("],\"schematron\":[");
    for(int i=0;i<rS.size();i++){ var r=rS.get(i);
      sb.append("{\"file\":\"").append(esc(r.file.toString())).append("\",\"ok\":").append(r.ok)
        .append(",\"failures\":").append(r.failures).append(",\"messages\":[");
      for(int j=0;j<r.messages.size();j++){ sb.append("\"").append(esc(r.messages.get(j))).append("\""); if(j<r.messages.size()-1) sb.append(","); }
      sb.append("]}"); if(i<rS.size()-1) sb.append(",");
    }
    sb.append("],\"lint\":[");
    for(int i=0;i<rL.size();i++){ var fr=rL.get(i);
      sb.append("{\"file\":\"").append(esc(fr.file.toString())).append("\",\"ok\":").append(fr.ok()).append(",\"warnings\":[");
      for(int j=0;j<fr.warnings.size();j++){ var w=fr.warnings.get(j);
        sb.append("{\"code\":\"").append(esc(w.code)).append("\",\"beats\":").append(w.beats);
        if(w.figureId!=null) sb.append(",\"figure\":\"").append(esc(w.figureId)).append("\"");
        if(w.meter!=null) sb.append(",\"meter\":\"").append(esc(w.meter)).append("\"");
        if(w.bars!=null) sb.append(",\"bars\":\"").append(esc(w.bars)).append("\"");
        if(w.message!=null) sb.append(",\"message\":\"").append(esc(w.message)).append("\"");
        sb.append("}"); if(j<fr.warnings.size()-1) sb.append(",");
      }
      sb.append("]}"); if(i<rL.size()-1) sb.append(",");
    }
    sb.append("]}");
    return sb.toString();
  }
}
