import requests

lat = 35.8149
lng = 128.5541
url = "https://m.land.naver.com/cluster/ajax/articleList"
params = {
    "rletTpCd": "VL:DDDGG:HOJT:JWJT:OR",
    "tradTpCd": "A1:B1:B2",
    "z": 16,
    "lat": lat,
    "lon": lng,
    "btm": lat - 0.005,
    "lft": lng - 0.01,
    "top": lat + 0.005,
    "rgt": lng + 0.01,
    "page": 1
}
res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, params=params)
print(res.json())