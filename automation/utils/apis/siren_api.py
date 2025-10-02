import requests
from typing import Dict, Any

base_url = "https://api.insee.fr/api-sirene/3.11/"
def get_data_from_siren_api(company_id: str, api_key: str) -> Dict[str, Any]:
    only_digits = ''.join(filter(str.isdigit, company_id))
    length = len(only_digits)
    if length == 14:
        return get_data_using_siret(only_digits, api_key)
    elif length == 9:
        return get_data_using_siren(only_digits, api_key)
    else:
        return {"error": "Invalid company ID format"}

def get_data_using_siret(siret: str, api_key: str) -> Dict[str, Any]:
    url = f"{base_url}siret/{siret}?champs=dateCreationUniteLegale%2C%20activitePrincipaleUniteLegale"
    headers = {
        "accept": "application/json",
        "X-INSEE-Api-Key-Integration": api_key,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        response = resp.json()
    except requests.RequestException as e:
        return {"error": f"Request failed: {e}"}
    except ValueError:
        return {"error": "Invalid JSON response"}

    ul = response.get("etablissement", {}).get("uniteLegale", {})
    return {
        "siren": siret[:9],
        "siret": siret,
        "date_creation": ul.get("dateCreationUniteLegale"),
        "naf_ape_code": ul.get("activitePrincipaleUniteLegale"),
    }

def get_data_using_siren(siren: str, api_key: str) -> Dict[str, Any]:
    url = f"{base_url}siren/{siren}?champs=dateCreationUniteLegale%2C%20activitePrincipaleUniteLegale"
    headers = {
        "accept": "application/json",
        "X-INSEE-Api-Key-Integration": api_key,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        response = resp.json()
    except requests.RequestException as e:
        return {"error": f"Request failed: {e}"}
    except ValueError:
        return {"error": "Invalid JSON response"}
    etab = response.get("uniteLegale", {})
    periodes = etab.get("periodesUniteLegale")
    naf_ape_code = None
    if isinstance(periodes, list) and periodes:
        naf_ape_code = periodes[0].get("activitePrincipaleUniteLegale")
    elif isinstance(periodes, dict):
        naf_ape_code = periodes.get("activitePrincipaleUniteLegale")

    return {
        "siren": siren,
        "siret": None,
        "date_creation": etab.get("dateCreationUniteLegale"),
        "naf_ape_code": naf_ape_code,
    }
