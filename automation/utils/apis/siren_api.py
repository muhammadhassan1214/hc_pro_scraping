import requests
from typing import Dict, Any


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
    url = (
        f"https://api.insee.fr/api-sirene/3.11/siret/{siret}?champs="
        "siren%2C%20siret%2C%20dateCreationEtablissement%2C%20activitePrincipaleUniteLegale%2C%20codePostalEtablissement"
    )
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

    etab = response.get("etablissement", {})
    siren = etab.get("siren")
    siret_val = etab.get("siret")
    date_creation = etab.get("dateCreationEtablissement")
    ul = etab.get("uniteLegale")
    naf_ape_code = ul.get("activitePrincipaleUniteLegale")
    return {
        "siren": siren,
        "siret": siret_val,
        "date_creation": date_creation,
        "naf_ape_code": naf_ape_code,
    }


def get_data_using_siren(siren: str, api_key: str) -> Dict[str, Any]:
    url = (
        f"https://api.insee.fr/api-sirene/3.11/siren/{siren}?champs="
        "siren%2C%20dateCreationUniteLegale%2C%20activitePrincipaleUniteLegale"
    )
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
    siren_val = etab.get("siren")
    date_creation = etab.get("dateCreationUniteLegale")
    # Defensive: periodesUniteLegale may be a list or dict, handle both
    periodes = etab.get("periodesUniteLegale")
    naf_ape_code = None
    if isinstance(periodes, list) and periodes:
        naf_ape_code = periodes[0].get("activitePrincipaleUniteLegale")
    elif isinstance(periodes, dict):
        naf_ape_code = periodes.get("activitePrincipaleUniteLegale")

    return {
        "siren": siren_val,
        "siret": None,
        "date_creation": date_creation,
        "naf_ape_code": naf_ape_code,
    }
