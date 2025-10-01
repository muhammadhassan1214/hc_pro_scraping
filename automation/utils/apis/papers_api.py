import requests

def get_data_from_papers_api(query: str, api_key: str) -> dict:
    url = "https://api.pappers.fr/v2/recherche"
    params = {
        "q": query,
        "api_token": api_key,
        "precision": "standard",
        "bases": "entreprises,dirigeants,publications",
        "page": 1,
        "par_page": 20,
        "case_sensitive": "false"
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.pappers.fr',
        'priority': 'u=1, i',
        'referer': 'https://www.pappers.fr/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers, params=params)
    r = response.json()["resultats"] if 'resultats' in response.json() else []
    print(response.status_code)
    if r and response.status_code == 200:
        siren = r[0].get("siren")
        siege = r[0].get("siege")
        siret = siege.get("siret")
        date_creation = r[0].get("date_creation")
        naf_ape_code = r[0].get("code_naf")

        return {
            "siren": siren,
            "siret": siret,
            "date_creation": date_creation,
            "naf_ape_code": naf_ape_code
        }
    return {}
