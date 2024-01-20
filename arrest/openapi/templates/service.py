from arrest import Resource, Service

{% for res in resource_list %}
{{ res }}
{% endfor %}

{{ service_identifier }} = Service(
    name={{ service_name }},
    url={{ service_url }},
    resources=[]
)
