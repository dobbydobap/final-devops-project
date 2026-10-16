{{/*
Release "studydesk" renders as "studydesk", any other release name as "<release>-studydesk".
The original always appended the chart name, which gave "studydesk-studydesk-backend" and broke
every hard-coded reference to "studydesk-backend".
*/}}
{{- define "studydesk.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end }}
