{{/* Fixed name — this chart is only ever deployed once per cluster, a
     templated release-name suffix would add nothing but noise. */}}
{{- define "orchestration-api.fullname" -}}
orchestration-api
{{- end -}}

{{- define "orchestration-api.labels" -}}
app: {{ include "orchestration-api.fullname" . }}
{{- end -}}
