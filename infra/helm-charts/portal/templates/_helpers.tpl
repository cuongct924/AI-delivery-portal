{{- define "portal.fullname" -}}
portal
{{- end -}}

{{- define "portal.labels" -}}
app: {{ include "portal.fullname" . }}
{{- end -}}
