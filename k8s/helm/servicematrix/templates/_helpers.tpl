{{/*
Expand the name of the chart.
*/}}
{{- define "servicematrix.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "servicematrix.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Chart label
*/}}
{{- define "servicematrix.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "servicematrix.labels" -}}
helm.sh/chart: {{ include "servicematrix.chart" . }}
app.kubernetes.io/name: {{ include "servicematrix.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels for a given component
Usage: {{ include "servicematrix.selectorLabels" (dict "root" . "component" "backend") }}
*/}}
{{- define "servicematrix.selectorLabels" -}}
app.kubernetes.io/name: {{ include "servicematrix.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Namespace
*/}}
{{- define "servicematrix.namespace" -}}
{{- .Values.global.namespace | default "servicematrix" }}
{{- end }}

{{/*
Image with optional registry prefix
*/}}
{{- define "servicematrix.image" -}}
{{- $registry := .root.Values.global.imageRegistry | default "" -}}
{{- printf "%s%s:%s" $registry .repository .tag -}}
{{- end }}

{{/*
ServiceAccount name
*/}}
{{- define "servicematrix.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "servicematrix.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
