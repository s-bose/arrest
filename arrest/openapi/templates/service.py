from arrest import Service, Resource
from arrest import Service, Resource

{% for res in resource_list %}
{{ res }}
{% endfor %}

{{ service_identifier }} = Service(
    name={{ service_name }},
    url={{ service_url }},
    resources=[]
)