import functools
from time import sleep
from haversine import haversine
from app.services.geolocation import coords_to_address
from src.classes import *
import requests
import httpx
import asyncio

BASE_API_URL = "https://new.land.naver.com/api/"
#Check Log 
#Time
IS_LOGGING = True

def get(url = "", params = {}):
    rep = requests.get(BASE_API_URL + url, params=params, headers={'User-Agent': '*'})
    if IS_LOGGING is True : print('Get', rep.request.url)
    if rep.status_code != 200: raise Exception('Response Error')
    return rep.json()

def get_neighborhood(sector : NSector, nType = ''):
    param = sector.loc.get_around_param()
    param.update({'zoom' : sector.loc.zoom})
    res = None
    if nType != NNeighbor.SCHOOL:
        param.update({ 'type' : nType})
        res = get(NRE_ROUTER.NEIGHBORHOOD, param)
    else:
        res = get(NRE_ROUTER.SCHOOL, param)
    return parse_neighbor(res, nType)

async def get_neighborhood_async(sector: NSector, nType: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(get_neighborhood, sector, nType))

async def async_get_all_neighbors(sector: NSector):
    tasks = [get_neighborhood_async(sector, nType) for nType in NNeighbor.EACH]
    results = await asyncio.gather(*tasks)
    neighbors = []
    for res in results:
        neighbors.extend(res)
    return neighbors

def make_param_thing(sector : NSector, addon : NAddon = NAddon.get_default()):
    param = {
        'zoom': sector.loc.zoom,
        'priceType': 'RETAIL',
        'markerId': '',
        'markerType': '',
        'selectedComplexNo': '',
        'selectedComplexBuildingNo': '',
        'fakeComplexMarker': '',
        'tag': '::::::::',
        'rentPriceMin':0,
        'rentPriceMax':900000000,
        'priceMin':0,
        'priceMax': 900000000,
        'areaMin':0,
        'areaMax':900000000,
        'oldBuildYears':'',
        'recentlyBuildYears':'',
        'minHouseHoldCount':'',
        'maxHouseHoldCount':'',
        'showArticle':True,
        'sameAddressGroup':False,
        'minMaintenanceCost':'',
        'maxMaintenanceCost':'',
    }
    param.update(sector.get_param())
    param.update(addon.get_param())
    return param

def get_things(sector: NSector, addon = NAddon.get_default()):
    res = get(NRE_ROUTER.COMPLEX2, make_param_thing(sector, addon))
    return parse_things(res, sector, addon.dir)

def make_param_sector(loc : NLocation):
    return  {'centerLat':loc.lat, 'centerLon':loc.lon, 'zoom': loc.zoom}

def get_sector(loc : NLocation):
    res = get(NRE_ROUTER.CORTARS, make_param_sector(loc))
    return parse_sector(res)

def split_list(list : list, k : int = 5):
    splited = []
    step = len(list) // k
    left = 0
    end = step * k
    while left < end:
        splited.append(list[left : left + step])
        left += step
    
    if left <= len(list):
        splited.append(list[left:])
    return splited


def default_loop(list):
    return list

def get_sector_list(regions : list[NRegion], delay : int = 2, interval : int = 10, loop = default_loop):
    sectors = []
    cancel = []
    loading = 0
    for reg in loop(regions):
        try:
            sector = get_sector(reg.loc)
            sectors.append(sector)
            loading += 1
            if loading == interval:
                sleep(delay)
                loading = 0
        except:
            print("Error", reg)
            cancel.append(reg)
            get_sleep(20)
            continue
    return sectors, cancel

def get_sleep(delay : int = 20):
    sleep(delay)

def make_param_region(code):
    return {'cortarNo': code}

def get_region_list(code = "0000000000"):
    res = get(NRE_ROUTER.REGION_LIST, make_param_region(code))
    return parse_region(res)

def parse_region(region_obj = {}):
    if len(region_obj) < 1:
        return []
    regions = [] # type: list[NRegion]
    for obj in region_obj['regionList']:
        regions.append(NRegion(
            obj['cortarName'],
            NLocation(obj['centerLat'], obj['centerLon']), 
            obj['cortarNo']))
    return regions

def parse_sector(sector_json : dict):
    return NSector(sector_json['sectorName'], NLocation(sector_json['centerLat'], sector_json['centerLon']) , sector_json['sectorNo'], sector_json['cityName'], sector_json['divisionName'], sector_json['cortarVertexLists'])

def parse_neighbor(data, nType):
    res = [] # type: list[NNeighbor]

    if nType != NNeighbor.SCHOOL:
        for v in data['neighborhoods']:
            res.append(NNeighbor(
                nType,
                v['name'],
                NLocation(v['latitude'], v['longitude'])
            ))
    else:
        for v in data:
            res.append(NNeighbor(
                'PUB_SCHOOL' if v['organizationType'] == '공립' else 'PRI_SCHOOL',
                v['schoolName'],
                NLocation(v['latitude'], v['longitude']),
            ))

    if nType == NNeighbor.PRESCHOOL or nType == NNeighbor.KID:
        res = filter_item(res, lambda x : len(x.name), lambda x,y: x.name in y.name and x.name != y.name)
    return res

def parse_things(results, sector : NSector, dir):
    smap = sector.map
    res = [] # type: list[NThing]
    for v in results:
        if 'minDealPrice' not in v and 'minLeasePrice' not in v:
            continue
        if v['dealCount'] == 0 and v['leaseCount'] == 0:
            continue

        thing = NThing(
            v['complexName'],
            v['realEstateTypeCode'],
            v['completionYearMonth'],
            NLocation(v['latitude'], v['longitude']),
            NArea(v['minArea'], v['maxArea'], v['representativeArea'], v['floorAreaRatio']),
            NPrice(v['minDealPrice'], v['maxDealPrice'], None if 'medianDealPrice' not in v else v['medianDealPrice']),
            NPrice(v['minLeasePrice'],v['maxLeasePrice'] , None if 'medianLeasePrice' not in v else v['medianLeasePrice']),
            NPrice(v['minDealUnitPrice'], v['maxDealUnitPrice'], None if 'medianDealUnitPrice' not in v else v['medianDealUnitPrice']),
            NPrice(v['minLeaseUnitPrice'], v['maxLeaseUnitPrice'], None if 'medianLeaseUnitPrice' not in v else  v['medianLeaseUnitPrice'])
        )

        if smap.contain(thing.loc):
            thing.dir = dir
            res.append(thing)
    return res

def distance_between(l1 : NLocation, l2 : NLocation):
    return round(haversine(l1.get_tuple(), l2.get_tuple(), unit='m'))

def get_distance_standard(standard = {}):
    default_standard = {
        'BUS': 500,
        'METRO' : 500,
        'INFANT' : 750,
        'PRESCHOOL' : 750,
        'PRI_SCHOOL' : 1000,
        'PUB_SCHOOL' : 1000,
        'HOSPITAL' : 2000,
        'PARKING' : 500, 
        'MART' : 500,
        'CONVENIENCE': 300,
        'WASHING': 500,
        'BANK' : 750,
        'OFFICE' : 1250
    }
    default_standard.update(standard)
    return default_standard

def things_to_dusts(things : list[NThing], dimension : NDimension):
    dusts = []
    for t in things:
        dusts.append(NDust(t.type, [
            dimension.fit_scale(t.loc.lat, dimension.x_scale), 
            dimension.fit_scale(t.loc.lon, dimension.y_scale, 1)
            ]))
    return dusts

def neighbors_to_dusts(neis : list[NNeighbor], dimension : NDimension):
    dusts = []
    for t in neis:
        dusts.append(NDust(t.type, [
            dimension.fit_scale(t.loc.lat, dimension.x_scale), 
            dimension.fit_scale(t.loc.lon, dimension.y_scale, 1)
            ]))
    return dusts

def neighbor_prefix_flt(lhs : NNeighbor, rhs : NNeighbor):
    return lhs.name in rhs.name

def filter_item(list, to_key, condition):
    items = sorted(list, key=to_key, reverse=True)
    res = []
    while len(items) > 0:
        item = items.pop()
        for it in items[:]:
            if condition(item, it) is True:
                items.remove(it)
        res.append(item)
    return res

def update_things_intersection(things : list[NThing], neighbors : list[NNeighbor], standard):
    for thing in things: # 매물
        around = NNeighborAround()
        for nei in neighbors: # 편의시설
            d = distance_between(thing.loc, nei.loc)
            if d <= standard[nei.type]: # meter
                around.increase(nei.type)
        thing.neiAround = around


def get_all_neighbors(sector):
    neighbors = [] # 편의시설 기록
    for nType in NNeighbor.EACH: # 모든 편의시설
        neighbors.extend(get_neighborhood(sector, nType))
    return neighbors

def get_things_each_direction(sector):
    # addon = NAddon(
    #     #direction=nc.NAddon.DIR_EACH, #전 방향 탐색
    #     tradeType=[NAddon.TRADE_DEAL, NAddon.TRADE_LEASE], #목표 거래 - 매매, 전세
    #     estateType=[NAddon.ESTATE_APT, NAddon.ESTATE_OPST] #목표 매물 - 아파트, 오피스텔
    # )
    addon = NAddon(
        tradeType=[NAddon.TRADE_DEAL, NAddon.TRADE_LEASE],
        estateType=[
            NAddon.ESTATE_APT,
            NAddon.ESTATE_OPST,
            NAddon.ESTATE_VILLA,
            NAddon.ESTATE_HOUSE,
            NAddon.ESTATE_TERRACE,
            NAddon.ESTATE_ONE_ROOM
        ]
    )
    things = [] # 매물 기록
    for dirr in NAddon.DIR_EACH: # 모든 방향 (남향 등등)
        addon.dir = dirr # 방향 조건 선택
        things.extend(get_things(sector, addon))
    return things

# 일반 매물 크롤링 (빌라/주택/원룸/투룸)
def get_articles_by_type(loc: NLocation, real_estate_types: list[str], trade_type="B1", page=1):
    params = {
        "realEstateType": ":".join(real_estate_types),
        "tradeType": trade_type,
        "latitude": loc.lat,
        "longitude": loc.lon,
        "order": "date",
        "showR0": "N",
        "page": page,
        "priceType": "RETAIL"
    }
    return get("articles/list", params)

def get_all_on_sector(sector : NSector):
    things = get_things_each_direction(sector)
    neighbors = get_all_neighbors(sector)
    return (sector, things, neighbors)

async def get_article_listings(loc: NLocation) -> list[dict]:
    listings = []
    url = "https://m.land.naver.com/cluster/ajax/articleList"
    params = {
        "rletTpCd": "VL:DDDGG:HOJT:JWJT:OR",
        "tradTpCd": "A1:B1:B2",
        "z": 16,
        "lat": loc.lat,
        "lon": loc.lon,
        "btm": loc.lat - 0.005,
        "lft": loc.lon - 0.01,
        "top": loc.lat + 0.005,
        "rgt": loc.lon + 0.01,
        "page": 1
    }

    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
        data = res.json()

        articles = data.get("body", [])
        coords_list = [(float(a["lat"]), float(a["lng"])) for a in articles]
        
        addresses = await asyncio.gather(*[
            coords_to_address(lat, lng) for lat, lng in coords_list
        ])

        for a, address_name in zip(articles, addresses):
            try:
                deposit = int(a.get("prc", 0))
                monthly = int(a.get("rentPrc", 0))
                area_m2 = float(a.get("spc2", 0) or 0.0)
                lat_a = float(a["lat"])
                lng_a = float(a["lng"])

                listings.append({
                    "name": a.get("atclNm", "매물"),
                    "address": address_name,
                    "area": round(area_m2, 1),
                    "deposit": deposit,
                    "monthly": monthly,
                    "price": deposit + monthly * 10,
                    "lat": lat_a,
                    "lng": lng_a,
                    "type": a.get("rletTpNm", "기타"),
                    "distance_km": round(distance_between(loc, NLocation(lat_a, lng_a)) / 1000, 2),
                    "source": "article"
                })
            except Exception as e:
                print(f"[article 파싱 실패] {e}")
    except Exception as e:
        print(f"[articleList 요청 실패] {e}")

    return listings

# 비동기 get_things
async def get_things_async(sector: NSector, addon: NAddon) -> list[NThing]:
    BASE_API_URL = "https://new.land.naver.com/api/"
    url = BASE_API_URL + "complexes/single-markers/2.0"
    params = make_param_thing(sector, addon)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers={'User-Agent': '*'}, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return parse_things(data, sector, addon.dir)
        except Exception as e:
            print(f"[비동기 매물 요청 실패] {addon.dir}: {e}")
            return []

# 병렬 방향 요청
async def async_get_parallel_things(sector: NSector) -> list[NThing]:
    directions = NAddon.DIR_EACH
    tasks = []

    for dirr in directions:
        addon = NAddon(
            dir=[dirr],
            tradeType=[NAddon.TRADE_DEAL, NAddon.TRADE_LEASE],
            estateType=[
                NAddon.ESTATE_APT,
                NAddon.ESTATE_OPST,
                NAddon.ESTATE_VILLA,
                NAddon.ESTATE_HOUSE
            ]
        )
        tasks.append(get_things_async(sector, addon))

    # asyncio.gather로 병렬 호출
    all_results = await asyncio.gather(*tasks, return_exceptions=False)

    # 리스트 합치기
    combined = []
    for sublist in all_results:
        combined.extend(sublist)

    return combined