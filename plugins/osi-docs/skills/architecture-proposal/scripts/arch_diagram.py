# ============================================================================
# arch_diagram.py — 段階対応・クラウドインフラ構成図ジェネレータ（テンプレート）
#
# 使い方: python3 arch_diagram.py <STAGE>   (STAGE=1/2/3)
#   → arch_v<STAGE>.svg を出力。PNG化は soffice:
#     soffice --headless --convert-to png arch_v1.svg
#
# このファイルは「コピーして案件ごとに編集する」テンプレートです。完全自動の
# 汎用エンジンにしていないのは、任意アーキの自動レイアウト／配線は壊れやすく、
# 既知の良い型を編集する方が速く確実だからです。編集ポイントは下記。
#
# ▼ 編集する場所（"EDIT" コメントを探す）
#  1) 色とブランド: RED(=自社/構築) / BLUE(=相手社/AI設計) / GRAY(=発注元) を担当に合わせる
#  2) ノード定義: node(x,y,w,h, owner, icon, l1, l2="", intro=段階)
#       owner = RED/BLUE/GRAY（箱の背景＝担当色・薄め）
#       icon  = lb/armor/iap/webapp/apigw/chat/agent/vertex/bigquery/dataform/
#               build/datastream/connector/memory/nat/globe（references/cloud-services.md 参照）
#       intro = そのコンポーネントが登場する段階(1/2/3)。STAGE未満は自動でグレーアウト、
#               STAGE==introは緑NEWバッジ。
#  3) グループ: group(x,y,w,h,label,stroke) でゾーン枠（エッジ/Cloud Run/データ/VPC 等）
#  4) 配線: oconn([(x1,y1),(x2,y2),...], color, dashed, label, lx, ly, intro=段階)
#  5) クラウド差し替え: AWSにするなら icon の種類とサービス名を AWS 用に。
#       GCP→AWS 対応は references/cloud-services.md。
#
# ▼ 守る作法（references/structure.md にも記載）
#  - 担当は「箱の背景色（薄）＋枠線色」で表す（凡例と一致させる）
#  - 段階(v1/v2/v3)は intro で制御し、3回レンダリングして3枚に分ける
#  - サブネットに public/private を持ち込まない（GCPはServerless VPC Access/Cloud NAT）
# ============================================================================

# -*- coding: utf-8 -*-
import sys
STAGE=int(sys.argv[1]) if len(sys.argv)>1 else 3
W,H=2400,1230
RED="#B91C1C"; BLUE="#1D4ED8"; GRAY="#374151"
GBLUE="#4285F4"; GBLUE2="#1A73E8"; GRED="#EA4335"; GYEL="#FBBC04"; GGREEN="#34A853"
TXT="#202124"; SUB="#5F6368"; BORD="#DADCE0"
def tint(hx,f=0.9):
    r=int(hx[1:3],16);g=int(hx[3:5],16);b=int(hx[5:7],16)
    return "#%02X%02X%02X"%(int(r+(255-r)*f),int(g+(255-g)*f),int(b+(255-b)*f))
F='font-family="Noto Sans CJK JP, sans-serif"'
el=[]; add=el.append
def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def rrect(x,y,w,h,fill,stroke="none",sw=0,rx=12,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} fill-opacity="{op}"/>')
def text(x,y,s,size=20,color=TXT,anchor="middle",weight="normal"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}" {F}>{esc(s)}</text>')
def ci(cx,cy,r,fill,op=1): add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" fill-opacity="{op}"/>')
def re(x,y,w,h,fill,rx=3,op=1): add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" fill-opacity="{op}"/>')
def pa(d,fill,op=1,stroke="none",sw=0): add(f'<path d="{d}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"/>')
def ln(x1,y1,x2,y2,color,sw=3,op=1): add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" stroke-opacity="{op}"/>')
def icon(k,ix,iy,s,op=1):
    cx,cy=ix+s/2,iy+s/2
    if k=="lb":
        ci(cx,iy+s*0.16,s*0.11,GBLUE,op)
        for dx in (-0.32,0,0.32):
            ln(cx,iy+s*0.22,cx+s*dx,iy+s*0.8,GBLUE2,3,op); ci(cx+s*dx,iy+s*0.85,s*0.1,GBLUE,op)
    elif k=="armor":
        pa(f"M {cx} {iy+s*0.08} L {ix+s*0.86} {iy+s*0.26} L {ix+s*0.86} {iy+s*0.55} Q {ix+s*0.86} {iy+s*0.84} {cx} {iy+s*0.94} Q {ix+s*0.14} {iy+s*0.84} {ix+s*0.14} {iy+s*0.55} L {ix+s*0.14} {iy+s*0.26} Z",GBLUE,op)
        pa(f"M {ix+s*0.34} {cy+s*0.02} L {ix+s*0.46} {cy+s*0.16} L {ix+s*0.68} {cy-s*0.16}",("none"),op,"#FFFFFF",4)
    elif k=="iap":
        pa(f"M {cx} {iy+s*0.08} L {ix+s*0.86} {iy+s*0.26} L {ix+s*0.86} {iy+s*0.55} Q {ix+s*0.86} {iy+s*0.84} {cx} {iy+s*0.94} Q {ix+s*0.14} {iy+s*0.84} {ix+s*0.14} {iy+s*0.55} L {ix+s*0.14} {iy+s*0.26} Z",GBLUE,op)
        ci(cx,cy-s*0.02,s*0.1,"#FFFFFF",op); re(cx-s*0.04,cy-s*0.02,s*0.08,s*0.2,"#FFFFFF",1,op)
    elif k=="webapp":
        re(ix+s*0.1,iy+s*0.14,s*0.8,s*0.66,GBLUE,4,op); re(ix+s*0.1,iy+s*0.14,s*0.8,s*0.16,GBLUE2,4,op)
        ci(ix+s*0.2,iy+s*0.22,s*0.03,"#FFFFFF",op); re(ix+s*0.2,iy+s*0.4,s*0.6,s*0.06,"#FFFFFF",2,op); re(ix+s*0.2,iy+s*0.54,s*0.4,s*0.06,"#FFFFFF",2,op)
    elif k=="apigw":
        re(ix+s*0.12,iy+s*0.16,s*0.76,s*0.68,GBLUE,7,op); text(ix+s*0.5,iy+s*0.66,"{ }",int(s*0.42),"#FFFFFF","middle","bold")
    elif k=="chat":
        pa(f"M {ix+s*0.12} {iy+s*0.16} L {ix+s*0.88} {iy+s*0.16} Q {ix+s*0.96} {iy+s*0.16} {ix+s*0.96} {iy+s*0.26} L {ix+s*0.96} {iy+s*0.6} Q {ix+s*0.96} {iy+s*0.7} {ix+s*0.86} {iy+s*0.7} L {ix+s*0.4} {iy+s*0.7} L {ix+s*0.24} {iy+s*0.86} L {ix+s*0.24} {iy+s*0.7} Q {ix+s*0.12} {iy+s*0.7} {ix+s*0.12} {iy+s*0.6} Z",GBLUE,op)
        re(ix+s*0.24,iy+s*0.32,s*0.12,s*0.24,"#FFFFFF",1,op); re(ix+s*0.44,iy+s*0.3,s*0.12,s*0.26,GYEL,1,op); re(ix+s*0.64,iy+s*0.34,s*0.12,s*0.22,GGREEN,1,op)
    elif k=="agent":
        re(ix+s*0.16,iy+s*0.26,s*0.68,s*0.56,GBLUE,10,op); ln(cx,iy+s*0.12,cx,iy+s*0.26,GBLUE2,3,op); ci(cx,iy+s*0.1,s*0.06,GBLUE,op)
        ci(ix+s*0.36,cy+s*0.04,s*0.07,"#FFFFFF",op); ci(ix+s*0.64,cy+s*0.04,s*0.07,"#FFFFFF",op)
    elif k=="vertex":
        pa(f"M {cx} {iy+s*0.1} L {cx+s*0.14} {cy} L {cx} {iy+s*0.9} L {cx-s*0.14} {cy} Z",GBLUE,op)
        pa(f"M {ix+s*0.1} {cy} L {cx} {cy-s*0.14} L {ix+s*0.9} {cy} L {cx} {cy+s*0.14} Z",GRED,op*0.9); ci(cx,cy,s*0.1,GYEL,op)
    elif k=="bigquery":
        add(f'<circle cx="{cx}" cy="{cy-s*0.04}" r="{s*0.3}" fill="none" stroke="{GBLUE}" stroke-width="{s*0.13}" stroke-opacity="{op}"/>')
        pa(f"M {cx} {cy-s*0.34} A {s*0.3} {s*0.3} 0 0 1 {cx+s*0.26} {cy+s*0.1}",("none"),op,GGREEN,int(s*0.13)); ln(cx+s*0.22,cy+s*0.22,cx+s*0.4,cy+s*0.4,GBLUE2,int(s*0.1),op)
    elif k=="dataform":
        re(ix+s*0.14,iy+s*0.16,s*0.72,s*0.68,GBLUE,6,op)
        for i in range(3): re(ix+s*0.22,iy+s*(0.28+i*0.18),s*0.56,s*0.08,"#FFFFFF",1,op)
    elif k=="build":
        import math; ci(cx,cy,s*0.18,GBLUE,op)
        for a in range(8):
            ang=a*math.pi/4; ln(cx+math.cos(ang)*s*0.2,cy+math.sin(ang)*s*0.2,cx+math.cos(ang)*s*0.34,cy+math.sin(ang)*s*0.34,GBLUE,int(s*0.1),op)
        ci(cx,cy,s*0.07,"#FFFFFF",op)
    elif k=="datastream":
        for i,c in enumerate([GBLUE,GBLUE2,GBLUE]):
            xo=ix+s*(0.2+i*0.22); pa(f"M {xo} {iy+s*0.3} L {xo+s*0.16} {cy} L {xo} {iy+s*0.7}",("none"),op,c,int(s*0.1))
    elif k=="connector":
        ci(ix+s*0.3,cy,s*0.12,GBLUE,op); ci(ix+s*0.7,cy,s*0.12,GGREEN,op); ln(ix+s*0.4,cy,ix+s*0.6,cy,SUB,int(s*0.09),op)
    elif k=="memory":
        re(ix+s*0.24,iy+s*0.24,s*0.52,s*0.52,GRED,5,op)
        for i in range(3):
            xo=ix+s*(0.34+i*0.16); ln(xo,iy+s*0.16,xo,iy+s*0.24,GRED,3,op); ln(xo,iy+s*0.76,xo,iy+s*0.84,GRED,3,op)
        re(ix+s*0.36,iy+s*0.36,s*0.28,s*0.28,"#FFFFFF",2,op)
    elif k=="nat":
        re(ix+s*0.14,iy+s*0.34,s*0.72,s*0.34,GBLUE,5,op); ci(ix+s*0.3,cy+s*0.02,s*0.05,"#FFFFFF",op); ci(ix+s*0.5,cy+s*0.02,s*0.05,"#FFFFFF",op); ci(ix+s*0.7,cy+s*0.02,s*0.05,"#FFFFFF",op)
    elif k=="globe":
        add(f'<circle cx="{cx}" cy="{cy}" r="{s*0.36}" fill="none" stroke="#9AA0A6" stroke-width="3" fill-opacity="{op}"/>')
        add(f'<ellipse cx="{cx}" cy="{cy}" rx="{s*0.16}" ry="{s*0.36}" fill="none" stroke="#9AA0A6" stroke-width="2"/>'); ln(cx-s*0.36,cy,cx+s*0.36,cy,"#9AA0A6",2,op)

def node(x,y,w,h,owner,kind,l1,l2="",intro=1):
    active=intro<=STAGE; new=(intro==STAGE and STAGE>1)
    if not active:
        rrect(x,y,w,h,"#F5F6F7","#D5D7DB",2,11,"6,5"); rrect(x+6,y+9,7,h-18,"#C7CBD1",3)
        icon(kind,x+20,y+h/2-14,28,op=0.28); tx=x+20+28+11
        if l2: text(tx,y+h/2-2,l1,17,"#AEB2B8","start","bold"); text(tx,y+h/2+19,l2,14,"#C2C5CB","start")
        else: text(tx,y+h/2+6,l1,17,"#AEB2B8","start","bold")
        return
    rrect(x,y,w,h,tint(owner,0.9),("#34A853" if new else owner),(3 if new else 1.6),11)
    icon(kind,x+18,y+h/2-14,28); tx=x+18+28+11
    if l2: text(tx,y+h/2-2,l1,18,TXT,"start","bold"); text(tx,y+h/2+19,l2,14,SUB,"start")
    else: text(tx,y+h/2+6,l1,18,TXT,"start","bold")
    if new: rrect(x+w-54,y+6,48,21,"#34A853",rx=6); text(x+w-30,y+20,"NEW",12,"#FFFFFF","middle","bold")
def group(x,y,w,h,label,stroke):
    rrect(x,y,w,h,"none",stroke,2.5,16); tw=len(label)*15+36; rrect(x+16,y-3,tw,34,stroke,rx=8); text(x+16+tw/2,y+21,label,19,"#FFFFFF","middle","bold")
def oconn(pts,color="#80868B",dashed=False,label="",lx=None,ly=None,intro=1):
    active=intro<=STAGE
    c = color if active else "#D5D7DB"; dd=' stroke-dasharray="8,6"' if (dashed or not active) else ""
    path="M "+" L ".join(f"{x} {y}" for x,y in pts)
    add(f'<path d="{path}" stroke="{c}" stroke-width="3.5" fill="none" marker-end="url(#ah)"{dd}/>')
    if label and active:
        mx,my=(lx,ly) if lx is not None else (pts[0][0],pts[0][1])
        rrect(mx-len(label)*7.5-6,my-16,len(label)*15+12,27,"#FFFFFF",rx=6,op=0.95); text(mx,my+3,label,15,SUB,"middle","bold")

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add('<defs><marker id="ah" markerWidth="11" markerHeight="11" refX="8" refY="5" orient="auto"><path d="M0,0 L9,5 L0,10 z" fill="#80868B"/></marker></defs>')
rrect(0,0,W,H,"#FFFFFF",rx=0)
# legend
lx=40; text(40,46,"担当：",19,TXT,"start","bold"); lx=160
for name,col in [("AI OSI URI＝構築",RED),("パートナー社＝AI設計（ノウハウ）",BLUE),("発注元＝要求・ADR",GRAY)]:
    rrect(lx,28,26,26,tint(col,0.9),col,1.6,5); text(lx+34,46,name,17,TXT,"start","bold"); lx+=len(name)*14+70
rrect(lx,28,26,26,"#F5F6F7","#D5D7DB",1.5,5,"5,4"); text(lx+34,46,"薄色＝未導入",16,SUB,"start"); lx+=230
rrect(lx,28,44,22,"#34A853",rx=5); text(lx+52,46,"＝本段階で追加",16,SUB,"start")

# GCP
GX,GY,GW,GH=560,100,1800,860
rrect(GX,GY,GW,GH,"#F8FBFF","#1A73E8",3,20)
add(f'<circle cx="{GX+42}" cy="{GY+16}" r="13" fill="{GBLUE}"/>'); text(GX+66,GY+24,"Google Cloud Platform（asia-northeast1）",20,GBLUE2,"start","bold")
gx0=GX+40; gw0=GW-80
# external API (intro2)
EAx=gx0+gw0-560
def extbox():
    act=2<=STAGE; new=(STAGE==2)
    if act:
        rrect(EAx,GY+10,560,52,"#FFFFFF",("#34A853" if new else "#9AA0A6"),(3 if new else 2),10); icon("globe",EAx+12,GY+20,32); text(EAx+58,GY+42,"外部API：SNS / トレンド / 天気 等",18,TXT,"start","bold")
        if new: rrect(EAx+560-54,GY+14,48,20,"#34A853",rx=6); text(EAx+560-30,GY+28,"NEW",12,"#FFFFFF","middle","bold")
    else:
        rrect(EAx,GY+10,560,52,"#F5F6F7","#D5D7DB",2,10,"6,5"); icon("globe",EAx+12,GY+20,32,op=0.3); text(EAx+58,GY+42,"外部API：SNS / トレンド / 天気 等",18,"#AEB2B8","start","bold")
extbox()

EGy=GY+50; group(gx0,EGy,gw0,100,"エッジ（Google Front End）","#1A73E8")
node(gx0+30,EGy+22,360,56,RED,"lb","Cloud Load Balancing")
node(gx0+420,EGy+22,320,56,RED,"armor","Cloud Armor (WAF)")
node(gx0+770,EGy+22,360,56,RED,"iap","Identity-Aware Proxy")
CRy=EGy+125; group(gx0,CRy,gw0,348,"Cloud Run（サーバーレス）","#B06000")
rA=CRy+40; rB=CRy+150; rC=CRy+255
c1=gx0+30; c2=gx0+445; c3=gx0+860; c4=gx0+1275; cw=395
node(c1,rA,cw,56,RED,"webapp","Web アプリ","BI + チャット UI")
node(c2,rA,cw,56,RED,"apigw","BFF / API Gateway")
node(c3,rA,cw,56,RED,"chat","分析 API","対話分析→Vega-Lite返却")
node(c4,rA,cw,56,RED,"apigw","write-back API",intro=3)
node(c1,rB,cw,56,BLUE,"agent","Orchestrator","ADK / A2A / MCP")
node(c2,rB,cw,56,BLUE,"agent","分析 / 提案 Agent")
node(c3,rB,cw,56,BLUE,"agent","文脈補完 Agent",intro=2)
node(c4,rB,cw,56,BLUE,"agent","実行 Agent",intro=3)
node(c1,rC,c4+cw-c1,46,BLUE,"vertex","Vertex AI / Gemini Enterprise（モデル基盤）")
# partner design region (rowB+rowC)
rrect(c1-12,rB-12,(c4+cw)-(c1-12),(rC+46)-(rB-12),"none",BLUE,2.5,14,"9,7")
text(c4+cw,rB-20,"← パートナー社：AIの設計・検討領域",15,BLUE,"end","bold")

DGy=CRy+372; group(gx0,DGy,gw0,118,"データ・分析（マネージド）","#7C3AED")
d1=gx0+30; d2=gx0+410; d3=gx0+960; d4=gx0+1330
node(d1,DGy+38,360,62,RED,"datastream","DTS / Datastream")
node(d2,DGy+38,520,62,RED,"bigquery","BigQuery","raw/gold/semantic 層（DB）")
node(d3,DGy+38,350,62,RED,"dataform","Dataform","Malloy/OSI YAML公開")
node(d4,DGy+38,330,62,RED,"build","Cloud Build")
VGy=DGy+148; group(gx0,VGy,gw0,118,"VPC ネットワーク","#188038")
node(gx0+30,VGy+38,440,62,RED,"connector","Serverless VPC Access","コネクタ")
node(gx0+500,VGy+38,360,62,RED,"memory","Memorystore (Redis)","Warm",intro=2)
node(gx0+890,VGy+38,300,62,RED,"nat","Cloud NAT","下り送信",intro=2)
text(gx0+1230,VGy+62,"※ Cloud RunはServerless VPC",14,SUB,"start")
text(gx0+1230,VGy+84,"  Access経由でVPCへ。外部APIは",14,SUB,"start")
text(gx0+1230,VGy+106,"  Cloud NAT経由（保存しない）",14,SUB,"start")
# source + actors
add(f'<rect x="{GX-330}" y="{DGy+38}" width="280" height="62" rx="11" fill="#fff" stroke="#9AA0A6" stroke-width="2"/>'); text(GX-330+140,DGy+76,"基幹・外部データ",18,TXT,"middle","bold")
ax=40
add(f'<rect x="{ax}" y="170" width="140" height="100" rx="11" fill="#fff" stroke="#5F6368" stroke-width="3"/>'); re(ax+12,182,116,26,"#5F6368",4); ci(ax+26,195,5,"#fff"); text(ax+70,300,"利用者（業務部門）",16,TXT,"middle","bold")
add(f'<rect x="{ax+25}" y="360" width="80" height="115" rx="11" fill="#fff" stroke="#5F6368" stroke-width="3"/>'); ci(ax+65,460,6,"#5F6368"); text(ax+65,505,"エンドクライアント",15,TXT,"middle","bold")
add(f'<rect x="{ax}" y="640" width="140" height="92" rx="11" fill="#fff" stroke="#5F6368" stroke-width="3"/>'); re(ax+45,732,46,14,"#5F6368",3); text(ax+70,778,"運用者端末",16,TXT,"middle","bold")
icx,icy=420,300
add(f'<ellipse cx="{icx}" cy="{icy}" rx="105" ry="62" fill="#F1F3F4" stroke="#9AA0A6" stroke-width="3"/>'); text(icx,icy+7,"インターネット",20,SUB,"middle","bold")
oconn([(195,220),(320,285)]); oconn([(160,410),(330,330)])

# arrows
oconn([(525,300),(gx0+30,EGy+50)],label="HTTPS",lx=545,ly=276)
oconn([(gx0+390,EGy+50),(gx0+420,EGy+50)])
oconn([(gx0+740,EGy+50),(gx0+770,EGy+50)])
oconn([(gx0+950,EGy+78),(gx0+950,CRy-12),(c1+190,CRy-12),(c1+190,rA)],label="認証",lx=gx0+560,ly=CRy-26)
oconn([(c1+cw,rA+28),(c2,rA+28)],label="要求",lx=c1+cw+10,ly=rA-2)
oconn([(c2+cw,rA+28),(c3,rA+28)],label="分析",lx=c2+cw+10,ly=rA-2)
oconn([(c2+200,rA+56),(c2+200,rB-10),(c1+190,rB-10),(c1+190,rB)],label="委譲",lx=c1+360,ly=rB-26)
oconn([(c1+cw,rB+28),(c2,rB+28)],"#1A73E8")
oconn([(c2+200,rB+56),(c2+200,rC)],"#1A73E8",label="モデル",lx=c2+260,ly=rC-12)
oconn([(c3+200,rB),(c3+200,GY+96),(EAx+200,GY+96),(EAx+200,GY+62)],dashed=True,label="Hot・保存しない",lx=c3+200,ly=GY+126,intro=2)
oconn([(d2+250,CRy+348),(d2+250,DGy+38)],label="クエリ/結果",lx=d2+250,ly=DGy-6)
oconn([(d1+150,CRy+348),(d1+150,VGy+38)],"#7C3AED",label="VPC接続",lx=d1+150,ly=VGy-8)
oconn([(GX-50,DGy+69),(d1,DGy+69)],label="取込",lx=GX-14,ly=DGy+18)
oconn([(d1+360,DGy+69),(d2,DGy+69)],"#B91C1C")
oconn([(d3,DGy+69),(d2+520,DGy+69)],"#B91C1C",label="公開",lx=d3+12,ly=DGy+18)
oconn([(c4+150,rA+56),(c4+150,DGy+10),(d2+360,DGy+10),(d2+360,DGy+38)],"#B91C1C",dashed=True,label="書戻し",lx=c4+150,ly=DGy-6,intro=3)

CY=GY+GH+24
rrect(GX,CY,GW,60,"#F1F3F4","#DADCE0",2,12)
text(GX+GW/2,CY+38,"横断：Cloud IAM ／ Secret Manager ／ VPC Service Controls ／ Cloud Logging・Monitoring ／ Cloud Build(CI/CD) ／ Terraform(IaC)",17,SUB,"middle","bold")
oconn([(110,732),(110,CY+30),(GX,CY+30)],label="運用・監視",lx=300,ly=CY+8)
FY=CY+80; rrect(40,FY,W-80,56,GRAY,rx=12)
text(W/2,FY+36,"発注元：要求定義・グランドデザイン・ADR（策定完了） ／ 分析対象データ提供",19,"#FFFFFF","middle","bold")
add('</svg>')
open(f"arch_v{STAGE}.svg","w").write("\n".join(el)); print("stage",STAGE,"ok")
