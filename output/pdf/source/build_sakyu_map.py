"""A4 landscape paper draft. Reads the website JSON without modifying it."""
import json
import math
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/pdf/scf2026-sakyu-paper-map-draft.pdf'
GEO = Path(__file__).with_name('osm-map-data.json')
if not GEO.exists():
    GEO = ROOT / 'tmp/pdfs/osm-map-data.json'
spots = json.loads((ROOT / 'data/spots.json').read_text())
events = json.loads((ROOT / 'data/events.json').read_text())
by_id = {s['id']: s for s in spots}
geo = json.loads(GEO.read_text())['elements']
pdfmetrics.registerFont(TTFont('JP', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
pdfmetrics.registerFont(TTFont('Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
W,H = landscape(A4)
c = canvas.Canvas(str(OUT), pagesize=(W,H))
c.setTitle('SCF2026 鳥取砂丘 Lunch & Sightseeing Map')
c.setAuthor('SCF2026')
NAVY='#1a365d'; BLUE='#2b6cb0'; GREEN='#276749'; INK='#2d3748'
MUTED='#566574'; LINE='#d8e0e6'; PALE='#edf4fa'; SAND='#f4eee0'

def norm(s):
    return str(s).replace('–','-').replace('〜','～')

def txt(x,y,s,size=8,color=INK,font='JP'):
    c.setFillColor(colors.HexColor(color)); c.setFont(font,size)
    c.drawString(x,y,norm(s))

def width(s,size=8,font='JP'):
    return pdfmetrics.stringWidth(norm(s),font,size)

def wrap(s,maxw,size=8,font='JP'):
    lines=[]; line=''
    for char in norm(s):
        if char=='\n' or (line and width(line+char,size,font)>maxw):
            lines.append(line); line=''
        if char!='\n': line+=char
    if line: lines.append(line)
    return lines

def para(x,y,s,maxw,size=8,leading=11,color=INK,font='JP'):
    for line in wrap(s,maxw,size,font):
        txt(x,y,line,size,color,font); y-=leading
    return y

def box(x,y,w,h,fill,stroke=None,r=0):
    c.setFillColor(colors.HexColor(fill))
    c.setStrokeColor(colors.HexColor(stroke or fill)); c.setLineWidth(.5)
    c.roundRect(x,y,w,h,r,fill=1,stroke=bool(stroke))

def rule(x,y,x2,color=LINE):
    c.setStrokeColor(colors.HexColor(color));c.setLineWidth(.5);c.line(x,y,x2,y)

def badge(x,y,id,size=15):
    color=BLUE if id.isdigit() else GREEN
    c.setFillColor(colors.HexColor(color))
    if id.isdigit(): c.roundRect(x,y,size,size,3,fill=1,stroke=0)
    else: c.circle(x+size/2,y+size/2,size/2,fill=1,stroke=0)
    sz=9 if size>=15 else 8
    txt(x+(size-width(id,sz,'Bold'))/2,y+(size-sz)/2+1,id,sz,'#ffffff','Bold')

def section(x,y,title,number=None):
    box(x,y-2,3,13,BLUE)
    txt(x+9,y,title,11,NAVY)

def project(lon,lat):
    return (6378137*math.radians(lon),6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2)))

def map_panel(x,y,w,h,bounds,ids,offsets,scale_m):
    west,south,east,north=bounds
    mx1,my1=project(west,south);mx2,my2=project(east,north)
    scale=min(w/(mx2-mx1),h/(my2-my1))
    cx=(mx1+mx2)/2;cy=(my1+my2)/2
    def pt(lon,lat):
        px,py=project(lon,lat)
        return x+w/2+(px-cx)*scale,y+h/2+(py-cy)*scale
    box(x,y,w,h,'#faf9f5',LINE)
    c.saveState(); clip=c.beginPath();clip.rect(x,y,w,h);c.clipPath(clip,stroke=0)
    def path(g):
        p=c.beginPath()
        for i,n in enumerate(g):
            px,py=pt(n['lon'],n['lat'])
            (p.moveTo if i==0 else p.lineTo)(px,py)
        return p
    for e in geo:
        tags=e.get('tags',{});g=e.get('geometry',[])
        fill=None
        if tags.get('natural')=='sand':fill=SAND
        elif tags.get('natural') in ('wood',) or tags.get('landuse') in ('forest','grass'):fill='#e4ecde'
        elif tags.get('natural')=='water':fill='#dcecf0'
        elif 'building' in tags:fill='#d6d5cf'
        if fill and len(g)>2:
            c.setFillColor(colors.HexColor(fill));p=path(g);p.close()
            is_building='building' in tags
            c.setStrokeColor(colors.HexColor('#a6aaa6'));c.setLineWidth(.4)
            c.drawPath(p,fill=1,stroke=int(is_building))
    for e in geo:
        t=e.get('tags',{});g=e.get('geometry',[])
        if not g or not ('highway' in t or 'aerialway' in t):continue
        hw=t.get('highway','')
        if hw in ('footway','path','steps','track'):
            c.setStrokeColor(colors.HexColor('#998461'));c.setLineWidth(.8);c.setDash(2,2)
            c.drawPath(path(g));c.setDash()
        elif 'aerialway' in t:
            c.setStrokeColor(colors.HexColor(GREEN));c.setLineWidth(1.4);c.setDash(4,2);c.drawPath(path(g));c.setDash()
        else:
            is_main=hw in ('primary','secondary','tertiary')
            roadwidth=5.8 if is_main else 2.8
            c.setStrokeColor(colors.HexColor('#b4ad99'));c.setLineWidth(roadwidth+1);c.drawPath(path(g))
            c.setStrokeColor(colors.HexColor('#ffedbb') if is_main else colors.white)
            c.setLineWidth(roadwidth);c.drawPath(path(g))
    c.restoreState()
    # Exact-coordinate anchors, with leader lines only for print label separation.
    for id in ids:
        spot=by_id[id];a,b=pt(spot['location']['longitude'],spot['location']['latitude'])
        dx,dy=offsets.get(id,(0,0));lx=a+dx;ly=b+dy
        color=BLUE if spot['type']=='food' else GREEN
        c.setStrokeColor(colors.HexColor(color));c.setFillColor(colors.HexColor(color));c.setLineWidth(.65)
        if dx or dy:
            c.line(a,b,lx,ly);c.circle(a,b,1.8,fill=1,stroke=0)
        badge(lx-8,ly-8,id,16)
        if id in ('B','C'):
            box(lx-13,ly+9,26,8,NAVY,r=2);txt(lx-11,ly+10.5,'EVENT',5.6,'#ffffff','Bold')
    # Ground-distance scale (Mercator scale corrected for latitude).
    lat=(south+north)/2
    length=scale_m/math.cos(math.radians(lat))*scale
    box(x+5,y+5,length+14,18,'#ffffff',r=2)
    c.setStrokeColor(colors.HexColor(INK));c.setLineWidth(.8)
    c.line(x+10,y+11,x+10+length,y+11)
    for sx in (x+10,x+10+length):c.line(sx,y+9,sx,y+13)
    txt(x+10,y+15,f'{scale_m} m',6.8,MUTED)
    box(x+w-23,y+h-28,18,23,'#ffffff',r=2)
    txt(x+w-17,y+h-14,'N',8,NAVY,'Bold')
    c.setStrokeColor(colors.HexColor(NAVY));c.setLineWidth(.8)
    c.line(x+w-14,y+h-25,x+w-14,y+h-17)
    c.line(x+w-14,y+h-17,x+w-17,y+h-20);c.line(x+w-14,y+h-17,x+w-11,y+h-20)
    return pt

def map_name(x,y,name,size=8,color=INK):
    """White halo preserves readable facility names over geographic detail."""
    c.saveState()
    c.addLiteral('/Artifact BMC')
    for dx,dy in [(-.7,0),(.7,0),(0,-.7),(0,.7),(-.5,-.5),(.5,.5),(-.5,.5),(.5,-.5)]:
        txt(x+dx,y+dy,name,size,'#ffffff')
    c.addLiteral('EMC')
    txt(x,y,name,size,color)
    c.restoreState()

# Header: SCF theme with generous white space.
txt(23,567,'SCF2026',16,NAVY,'Bold')
txt(130,567,'鳥取砂丘',19,NAVY)
txt(225,567,'Lunch & Sightseeing Map',20,NAVY,'Bold')
txt(130,543,'2026.10.24 Sat.',14,NAVY,'Bold')
txt(250,543,'11:30-14:30',14,BLUE,'Bold')
rule(23,533,747,NAVY)

# Maps.
section(23,513,'エリアマップ')
badge(172,510,'01',12);txt(189,512,'飲食店',8)
badge(232,510,'B',12);txt(249,512,'観光',8)
main_ids=['B','07','01','12','03','04','02','E','08','D','15','C']
offsets={'B':(-47,10),'07':(20,-3),'01':(26,3),'12':(28,2),
         '03':(-49,4),'04':(-47,-6),'02':(-5,27),'E':(15,27),
         '08':(-49,-5),'D':(27,8),'15':(-67,15),'C':(29,12)}
# The north-south corridor is enlarged; A remains in the list only.
pt=map_panel(23,128,250,371,(134.2361,35.5393,134.2393,35.54495),main_ids,offsets,50)
px1,py1=pt(134.23635,35.54128);px2,py2=pt(134.23712,35.54235)
c.setStrokeColor(colors.HexColor(BLUE));c.setLineWidth(1.1);c.setDash(3,2);c.rect(px1,py1,px2-px1,py2-py1);c.setDash()
map_name(31,312,'右の拡大図へ',8,BLUE)
map_name(31,481,'鳥取砂丘',10,'#8c7b58')
names={
    'B':(57,443,'ビジターセンター'),
    '07':(186,473,'レイガーデン'),
    '01':(174,420,'砂丘会館'),
    '12':(165,395,'タカハマカフェ'),
    '03':(77,369,'らくだや'),
    '04':(70,339,'スカット'),
    '02':(176,315,'砂丘センター'),
    'E':(178,283,'眺望テラス'),
    '08':(68,212,'村上水産'),
    'D':(163,267,'観光リフト'),
    '15':(84,165,'砂丘コーヒー'),
    'C':(194,143,'砂の美術館'),
}
for id,(tx,ty,name) in names.items():
    map_name(tx,ty,name,7.8,GREEN if by_id[id]['type']=='sightseeing' else INK)
# Road label follows a named road in the retained OSM geometry.
road=next(e for e in geo if e['id']==1546928857)
start,end=road['geometry'][0],road['geometry'][-1]
road_x,road_y=pt(start['lon']*.8+end['lon']*.2,start['lat']*.8+end['lat']*.2)
c.saveState();c.translate(road_x+9,road_y+5);c.rotate(90)
map_name(0,0,road['tags']['name'],7.2,'#71613f')
c.restoreState()

# Close-up uses the same coordinates, with separate labels for shared locations.
section(285,488,'店舗密集エリア 拡大図')
inset_offsets={'05':(-39,0),'06':(-22,10),'09':(-47,23),'10':(-47,0),
               '11':(38,27),'14':(41,0),'16':(-42,-23),'13':(-26,0)}
map_panel(285,247,143,229,(134.23636,35.54130,134.23713,35.54230),list(inset_offsets),inset_offsets,20)
box(285,128,143,108,'#f7f9fb',LINE,r=4)
txt(294,222,'地図の見方',9,NAVY)
c.setFillColor(colors.HexColor(BLUE));c.circle(298,207,2,fill=1,stroke=0)
txt(307,204,'点：実際の店舗・施設の位置',7.5)
txt(294,191,'線の先の番号を一覧と照合',7.5)
c.setStrokeColor(colors.HexColor('#998461'));c.setLineWidth(.8);c.setDash(2,2);c.line(294,180,311,180);c.setDash()
txt(317,177,'歩道等',7.5)
c.setStrokeColor(colors.HexColor(GREEN));c.setLineWidth(1.4);c.setDash(4,2);c.line(294,166,311,166);c.setDash()
txt(317,163,'観光リフト',7.5)
txt(294,148,'両図とも北が上／IDはWebと共通',7)
txt(294,136,'A 馬の背は地図範囲外です。',7,MUTED)
txt(23,117,'地図 © OpenStreetMap contributors | https://www.openstreetmap.org/copyright',6.3,MUTED)

# Food table.
X=443; R=819
section(X,513,'飲食店 01-16')
txt(X+125,513,'食事の終了時刻にご注意ください',8,MUTED)
box(X,489,R-X,17,PALE)
for xx,s in [(X+4,'ID'),(X+26,'店舗名'),(623,'SCF時間内'),(727,'価格帯（目安）')]:txt(xx,494,s,8,NAVY)
y=489
for spot in spots[:16]:
    id=spot['id']; h=23 if id in ('01','07') else 15
    if int(id)%2==0:box(X,y-h,R-X,h,'#f7f9fb')
    badge(X+4,y-h/2-6,id,12)
    name_size=8.1
    name_lines=wrap(spot['name'],146,name_size)
    assert len(name_lines)==1,(spot['name'],name_lines)
    txt(X+26,y-h/2-2.8,spot['name'],name_size)
    times=spot['eventHours'].split('／')
    for i,t in enumerate(times):
        assert width(t,8) <= 98, t
        txt(623,y-9-i*10 if len(times)>1 else y-h/2-2.8,t,8,BLUE)
    price=spot['price'].replace('程度','')
    txt(727,y-h/2-2.8,price,8)
    rule(X,y-h,R);y-=h
assert y>=231,y
box(X,207,R-X,23,'#faf3e7',r=3)
txt(X+6,221,'01・02 食事14:00まで ／ 06 L.O.13:30 ／ 07 料理L.O.14:00',8,'#765020')
txt(X+6,211,'06 鯛喜：1日50食限定。売り切れや予約で完売する場合があります。',7.4,'#765020')

# Sightseeing table, all share the time range from JSON.
section(X,190,'観光 A-E')
assert all(s['eventHours']=='11:30–14:30' for s in spots[16:])
txt(X+87,190,'SCF時間内 11:30-14:30',8.5,BLUE)
txt(X+237,190,'B・Cはイベント会場（下欄）',8,MUTED)
y=181
for spot in spots[16:]:
    id=spot['id']
    price_lines=wrap(spot['price'],R-(X+175),7.8)
    h=13+10*(len(price_lines)-1)
    badge(X+4,y-11,id,11)
    txt(X+22,y-8.5,spot['name'],8)
    for i,line in enumerate(price_lines):
        txt(X+175,y-8.5-10*i,line,7.8)
    rule(X,y-h,R);y-=h

# Events and a blank gathering box.
section(23,103,'10/24 開催イベント')
txt(179,103,'SCF時間内の時間を表示。詳細はWeb版へ。',7.4,MUTED)

def event_head(x,w,event,title,subtitle):
    txt(x,90,event['id'],8,BLUE,'Bold')
    txt(x+28,90,f"会場 {event['venueRef']}",8,GREEN)
    yy=para(x,77,title,w,8.3,10,NAVY)
    txt(x,yy-1,event['scfEventHours']+'  '+subtitle,8,BLUE)
    return yy-13

yy=event_head(23,184,events[0],'Meet the KIRINJISHI！\nin 鳥取砂丘','観覧無料')
para(23,yy,'麒麟獅子舞の披露・ふれあい。予約不要。\nアンケート回答者に先着プレゼント。',184,7.5,10)
yy=event_head(217,190,events[1],events[1]['name'],'')
para(217,yy,'みんなでハロウィン砂像を制作。\n料金：公式案内に記載なし。\n参加方法は公式案内をご確認ください。',190,7.5,10)
yy=event_head(417,244,events[2],'ミニ砂像体験［砂美ワークショップ2026］','')
txt(417,yy,'1体500円（道具レンタル込み）＋別途入館券',7.5)
txt(417,yy-11,'雨天中止／砂像の持ち帰り不可',8,'#765020')
txt(417,yy-21,'当日受付・先着順／定員10組／制作約30-40分',7.5,'#765020')
txt(417,yy-31,'混雑時は待ち時間が発生する場合があります。',7.1,MUTED)

# Gathering details are announced through Slack.
box(677,24,142,89,'#ffffff',LINE,r=3)
txt(686,98,'集合のご案内',9,NAVY)
txt(686,73,'集合場所と集合時刻は',11,NAVY)
txt(686,54,'Slackにて連絡します',11,NAVY)
# QR occupies the top-right header; the gathering box uses its former space.
url='https://hskkbr.github.io/scf2026-website/sakyu-map.html'
qr=QrCodeWidget(url,barLevel='M',barBorder=4)
bb=qr.getBounds(); qsize=58
d=Drawing(qsize,qsize,transform=[qsize/(bb[2]-bb[0]),0,0,qsize/(bb[3]-bb[1]),0,0]);d.add(qr)
renderPDF.draw(d,c,761,527)
c.linkURL(url,(761,527,819,585),relative=0,thickness=0)
txt(658,567,'Web版マップ',10,NAVY)
txt(658,553,'詳細・公式リンク',8,MUTED)
txt(658,541,'Google Maps',8,MUTED)

# Source and freshness notes. Neither the draft date nor meeting time is substituted.
rule(23,20,665)
latest=max(s['lastVerified'] for s in spots+events)
txt(23,10,f"情報最終確認：{int(latest[:4])}年{int(latest[5:7])}月{int(latest[8:])}日。営業時間・内容は変更される場合があります。最新情報は各公式情報をご確認ください。",6.5,MUTED)
c.showPage();c.save()
print(OUT)
