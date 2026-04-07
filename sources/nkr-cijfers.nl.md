
```python
import requests

body = {
    "language": "nl-NL",
    "groupBy": [
        {
            "code": "filter/stadium",
            "values": [
                {"code": "stadium/0"},
                {"code": "stadium/i"},
                {"code": "stadium/ii"},
                {"code": "stadium/iii"},
                {"code": "stadium/iv"},
                {"code": "stadium/x"},
                {"code": "stadium/nvt"}
            ]
        }
    ],
    "aggregateBy": [
        {
            "code": "filter/kankersoort",
            "values": [
                {"code": "kankersoort/totaal/alle"}
            ]
        },
        {
            "code": "filter/periode-van-diagnose",
            "values": [
                {"code": "periode/1-jaar/2024"}
            ]
        },
        {
            "code": "filter/geslacht",
            "values": [
                {"code": "geslacht/totaal/alle"}
            ]
        },
        {
            "code": "filter/leeftijdsgroep",
            "values": [
                {"code": "leeftijdsgroep/totaal/alle"}
            ]
        },
        {
            "code": "filter/regio",
            "values": [
                {"code": "regio/totaal/alle"}
            ]
        }
    ],
    "navigation": {
        "code": "incidentie/verdeling-per-stadium"
    },
    "statistic": {
        "code": "statistiek/verdeling"
    }
}

requests.post("https://api.nkr-cijfers.iknl.nl/api/data?format=json", json=body).json()
```