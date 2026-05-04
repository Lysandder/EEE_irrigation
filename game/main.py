#!/usr/bin/env python3
"""
Smart Irrigation Controller — pygame (v2)
PUMP = T ^ ((S ^ ¬R) v M)
"""
import pygame, sys, math, random
pygame.init()
# ── Display ───────────────────────────────────────────────────────────────────
info = pygame.display.Info()
W, H = info.current_w, info.current_h - 50
scr = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption("Smart Irrigation Controller")
clk = pygame.time.Clock()
# ── Fonts (Liberation Sans = crisp, thick, very readable) ───────────────────
def mf(sz, bold=False):
    for n in ["liberationsans","freesans","dejavusans","arial","verdana","ubuntu"]:
        try:
            f = pygame.font.SysFont(n, sz, bold=bold)
            return f
        except: pass
    return pygame.font.Font(None, sz + 10)

F_HUGE = mf(30, True)   # pump status
F_HEAD = mf(24, True)   # view headings
F_BTN  = mf(19, True)   # button labels
F_BODY = mf(17, True)   # table text (bold so it's visible)
F_SUB  = mf(14, True)   # secondary labels
F_TINY = mf(13, True)   # trace/legend
# ── Layout ────────────────────────────────────────────────────────────────────
TAB_H  = 54
BOT_H  = 140
MAIN_Y = TAB_H
MAIN_H = H - TAB_H - BOT_H
GRASS_Y = MAIN_Y + int(MAIN_H * 0.46)
GRASS_H = 15
UG_Y    = GRASS_Y + GRASS_H
UG_H    = H - BOT_H - UG_Y
SOIL_W  = int(W * 0.38)
PUMP_CX = int(W * 0.52)
PUMP_CY = UG_Y + UG_H // 2
TANK_X  = int(W * 0.74)
TANK_Y  = UG_Y + 12
TANK_W  = int(W * 0.18)
TANK_H  = UG_H - 26
# Bottom bar rows — 5 equal columns: [S][R][T][M][RAND]
NCOLS  = 5
COL_W  = W // NCOLS
BPAD   = 16
ROW1_Y = H - BOT_H + 9
ROW1_H = 56
ROW2_Y = ROW1_Y + ROW1_H + 9
ROW2_H = 48
BTN_RECTS = [pygame.Rect(i*COL_W + BPAD, ROW1_Y, COL_W - BPAD*2, ROW1_H) for i in range(4)]
RAND_R  = pygame.Rect(4*COL_W + BPAD, ROW1_Y, COL_W - BPAD*2, ROW1_H)
PUMP_R  = pygame.Rect(BPAD, ROW2_Y, W//2 - BPAD*2, ROW2_H)
COMBO_R = pygame.Rect(W//2 + BPAD, ROW2_Y, W//2 - BPAD*2, ROW2_H)
# ── Colors ────────────────────────────────────────────────────────────────────
SKY_T=(26,88,165);   SKY_B=(86,165,220)
GRASS_C=(48,142,48); SOIL_D=(126,71,26); SOIL_M=(60,32,7)
UG_C=(8,10,18);      PIPE_C=(83,94,108); WATER_C=(48,126,206)
TANK_O=(136,146,158); PMP_ON=(38,192,98); PMP_OFF=(178,38,38)
CLOUD_C=(200,215,235); CLOUD_R=(145,162,182)
SUN_C=(244,204,44);  SUN_R=(55,55,35);  RAIN_C=(118,160,210)
NAV_C=(14,16,34);    BOT_C=(16,19,38)
C_WH=(235,240,252);  C_MUT=(108,124,152)
C_ACN=(48,156,238);  C_GRN=(48,210,102)
C_RED=(228,68,68);   C_AMB=(234,180,50)
C_BLU=(73,148,240);  C_PUR=(158,102,240)
C_WON=(50,218,106);  C_WOFF=(36,56,44)
C_GAND=(20,75,35);   C_GOR=(18,38,72)
C_GNOT=(65,16,40);   C_GPUR=(38,12,60)
C_DISA=(40,44,68)    # disabled button bg

def lerpc(a, b, t):
    return tuple(max(0, min(255, int(a[i]+(b[i]-a[i])*t))) for i in range(3))
# ── Logic ─────────────────────────────────────────────────────────────────────
def pump_on(s, r, t, m): return bool(t and ((s and not r) or m))
def gsigs(s, r, t, m):
    g1=not r; g2=bool(s and g1); g3=bool(g2 and t)
    g4=bool(t and m); g5=bool(g3 or g4)
    return {'g1':g1,'g2':g2,'g3':g3,'g4':g4,'g5':g5,'pump':g5}

TC=[
    ("TC-01",1,0,1,0,True,  "Ideal: dry soil, no rain, tank full"),
    ("TC-02",0,0,1,0,False, "Moist soil — irrigation not needed"),
    ("TC-03",1,1,1,0,False, "Rain detected — conserve water"),
    ("TC-04",1,0,0,0,False, "Tank empty — cannot pump"),
    ("TC-05",0,0,0,1,False, "Manual override but tank empty"),
    ("TC-06",0,0,1,1,True,  "Manual override + water → ON"),
    ("TC-07",1,1,1,1,True,  "Rain + manual → override wins"),
    ("TC-08",1,0,1,1,True,  "All conditions met + manual"),
    ("TC-09",0,1,0,0,False, "Rain, no tank, moist — OFF"),
    ("TC-10",0,1,1,0,False, "Full tank but raining — still OFF"),
]
# ── State ─────────────────────────────────────────────────────────────────────
inp = [False]*4   # S, R, T, M
view = 'scene'
timer = 0.0
tank_lv = 0.0
pump_anim = 0.0
tr_scroll = 0
tc_scroll = 0
clouds=[]; rain_drops=[]; grass_blades=[]

def get_pump(): return pump_on(*inp)
def cidx(): return inp[0]*8+inp[1]*4+inp[2]*2+inp[3]
def cbits(): return ''.join('1' if x else '0' for x in inp)
def manual_on(): return inp[3]  # M is index 3

def init_world():
    global clouds, rain_drops, grass_blades
    clouds=[{'x':random.randint(0,W),'y':random.randint(MAIN_Y+20,GRASS_Y-85),
             'r':random.randint(30,58),'sp':random.uniform(0.12,0.35),
             'n':random.randint(3,5)} for _ in range(4)]
    rain_drops=[{'x':random.uniform(-50,W+50),'y':random.uniform(MAIN_Y,GRASS_Y),
                 'sp':random.uniform(6,13),'ln':random.randint(8,17)} for _ in range(140)]
    rng=random.Random(42)
    grass_blades=[(gx,rng.randint(-8,-3),rng.randint(-3,3)) for gx in range(0,W,14)]

init_world()
# ── Draw helpers ──────────────────────────────────────────────────────────────
def tx(text, fnt, col, cx, cy, anchor='c'):
    s=fnt.render(str(text), True, col)
    r=s.get_rect()
    if anchor=='c': r.center=(cx,cy)
    elif anchor=='l': r.midleft=(cx,cy)
    elif anchor=='r': r.midright=(cx,cy)
    scr.blit(s, r)

def rr(rect, rad, col, bw=0, bc=None):
    pygame.draw.rect(scr, col, rect, border_radius=rad)
    if bw and bc:
        pygame.draw.rect(scr, bc, rect, bw, border_radius=rad)

def cloud_sh(cx, cy, r, col, n=4):
    offs=[(-r*.60,r*.18),(0,0),(r*.60,r*.14),(-r*.28,-r*.32),(r*.24,-r*.28)]
    szs =[r*.75, r, r*.80, r*.65, r*.60]
    for i in range(min(n, len(offs))):
        ox,oy=offs[i]
        pygame.draw.circle(scr,col,(int(cx+ox),int(cy+oy)),int(szs[i]))

def wline(x1, y1, x2, y2, active):
    col=C_WON if active else C_WOFF
    pygame.draw.line(scr,col,(x1,y1),(x2,y2),3)
    if active:
        pygame.draw.line(scr,lerpc(C_WON,(200,255,220),.4),(x1,y1),(x2,y2),1)

def gbox(x, y, label, tcol, bgcol, w=84, h=34):
    rr((x,y-h//2,w,h),7,bgcol,2,tcol)
    tx(label,F_TINY,tcol,x+w//2,y)
    return x+w, y
# ══════════════════════════════════════════════════════════════════════════════
# SCENE
# ══════════════════════════════════════════════════════════════════════════════
def draw_scene():
    global tank_lv, pump_anim
    rain=inp[1]; po=get_pump()
    # Sky gradient
    sky_h=GRASS_Y-MAIN_Y
    for y in range(sky_h):
        pygame.draw.line(scr,lerpc(SKY_T,SKY_B,y/sky_h),(0,MAIN_Y+y),(W,MAIN_Y+y))
    # Sun
    if not rain:
        sx=int(W*.88); sy=MAIN_Y+int(sky_h*.26); sr=40
        for i in range(10):
            ang=i/10*math.tau+timer*.35
            x1=sx+math.cos(ang)*(sr+8);  y1=sy+math.sin(ang)*(sr+8)
            x2=sx+math.cos(ang)*(sr+25); y2=sy+math.sin(ang)*(sr+25)
            pygame.draw.line(scr,SUN_C,(int(x1),int(y1)),(int(x2),int(y2)),3)
        pygame.draw.circle(scr,SUN_R,(sx,sy),sr+5)
        pygame.draw.circle(scr,SUN_C,(sx,sy),sr)
        pygame.draw.circle(scr,lerpc(SUN_C,(255,255,210),.5),(sx-10,sy-10),12)
    # Clouds
    cc=CLOUD_R if rain else CLOUD_C
    for c in clouds:
        cloud_sh(int(c['x']),int(c['y']),c['r'],cc,c['n'])
    # Rain
    if rain:
        for d in rain_drops:
            x1,y1=int(d['x']),int(d['y'])
            pygame.draw.line(scr,RAIN_C,(x1,y1),(x1-int(d['ln']*.25),y1+d['ln']),1)
    # Grass + blades
    pygame.draw.rect(scr,GRASS_C,(0,GRASS_Y,W,GRASS_H))
    dark_g=lerpc(GRASS_C,(0,0,0),.35)
    for gx,gh,goff in grass_blades:
        pygame.draw.line(scr,dark_g,(gx,GRASS_Y),(gx+goff,GRASS_Y+gh),1)
    # Underground
    pygame.draw.rect(scr,UG_C,(0,UG_Y,W,UG_H))
    # Soil (left)
    sc=SOIL_D if inp[0] else SOIL_M
    pygame.draw.rect(scr,sc,(0,UG_Y,SOIL_W,UG_H))
    rng=random.Random(42)
    for i in range(45):
        dx=rng.randint(5,SOIL_W-5); dy=UG_Y+rng.randint(5,UG_H-5)
        pygame.draw.circle(scr,lerpc(sc,(0,0,0),.40),(dx,dy),rng.randint(2,6))
    if not inp[0]:
        mp=random.Random(77)
        for i in range(14):
            px=mp.randint(10,SOIL_W-10); py=UG_Y+mp.randint(10,UG_H-10)
            pygame.draw.circle(scr,lerpc(WATER_C,sc,.45),(px,py),3)
    pygame.draw.line(scr,PIPE_C,(SOIL_W,UG_Y),(SOIL_W,UG_Y+UG_H),2)
    slbl="DRY" if inp[0] else "MOIST"
    tx(slbl,F_BTN,C_AMB if inp[0] else C_BLU,SOIL_W//2,UG_Y+UG_H-20)
    # Pipes
    py_pipe=PUMP_CY+30
    pygame.draw.rect(scr,PIPE_C,(SOIL_W-10,py_pipe-7,W-SOIL_W+10,14),border_radius=7)
    pygame.draw.rect(scr,lerpc(PIPE_C,(200,212,222),.28),(SOIL_W-10,py_pipe-6,W-SOIL_W+10,4))
    pygame.draw.rect(scr,PIPE_C,(PUMP_CX-6,PUMP_CY+10,12,py_pipe-PUMP_CY-10),border_radius=4)
    pygame.draw.rect(scr,PIPE_C,(TANK_X+TANK_W//2-6,py_pipe-20,12,26),border_radius=4)
    # Water flow
    if po:
        span=TANK_X+TANK_W//2-SOIL_W
        for i in range(8):
            p=((timer*.65)+(i/8))%1.0
            # wx=SOIL_W+int(span*p)
            wx=TANK_X+TANK_W//2-int(span*p)
            alpha=1-abs(p-.5)*1.8
            if alpha>0:
                # pygame.draw.circle(scr,C_WON,(wx,py_pipe),max(2,int(5*alpha)))
                pygame.draw.circle(scr,C_BLU,(wx,py_pipe),max(2,int(5*alpha)))
    # Tank
    target=1.0 if inp[2] else 0.06
    tank_lv+=(target-tank_lv)*.06
    rr((TANK_X,TANK_Y,TANK_W,TANK_H),8,TANK_O,3,lerpc(TANK_O,(210,222,232),.3))
    ix=TANK_X+8; iw=TANK_W-16
    wh=int((TANK_H-16)*tank_lv)
    if wh>2:
        wy=TANK_Y+TANK_H-8-wh
        pygame.draw.rect(scr,WATER_C,(ix,wy,iw,wh),border_radius=5)
        sh=math.sin(timer*2.2)*2
        pygame.draw.line(scr,lerpc(WATER_C,(170,220,255),.45),(ix+4,wy+2+int(sh)),(ix+iw-4,wy+2+int(sh)))
    tx("FULL" if inp[2] else "EMPTY",F_BTN,C_GRN if inp[2] else C_RED,TANK_X+TANK_W//2,UG_Y+UG_H-20)
    # Pump
    pump_anim+=0.09
    pw,ph=68,88; px0=PUMP_CX-pw//2; py0=PUMP_CY-ph//2
    pcol=PMP_ON if po else PMP_OFF
    if po:
        pulse=abs(math.sin(pump_anim))*.55+.45
        for g in range(5,0,-1):
            gc=lerpc(pcol,UG_C,1-g*.18*pulse)
            pygame.draw.rect(scr,gc,(px0-g*3,py0-g*3,pw+g*6,ph+g*6),border_radius=14+g*2)
    rr((px0,py0,pw,ph),12,pcol,2,lerpc(pcol,(230,240,230),.35))
    for i in range(3):
        pygame.draw.line(scr,lerpc(pcol,(0,0,0),.45),(px0+8,py0+18+i*20),(px0+pw-8,py0+18+i*20),2)
    badge=(28,155,70) if po else (155,28,28)
    pygame.draw.circle(scr,badge,(PUMP_CX,py0-15),18)
    pygame.draw.circle(scr,lerpc(badge,(230,235,230),.35),(PUMP_CX,py0-15),18,2)
    tx("ON" if po else "OFF",F_SUB,C_WH,PUMP_CX,py0-15)
# ══════════════════════════════════════════════════════════════════════════════
# TRUTH TABLE
# ══════════════════════════════════════════════════════════════════════════════
COL_N=["S","R","T","M","¬R","S^¬R","S^¬R^T","T^M","g3vg4","PUMP"]
COL_C=[C_AMB,C_BLU,C_GRN,C_PUR,C_BLU,C_AMB,C_AMB,C_PUR,C_ACN,C_WH]
COL_W=[50,50,50,50,55,72,86,65,78,82]

def draw_truth_table():
    global tr_scroll
    pygame.draw.rect(scr,(8,10,18),(0,MAIN_Y,W,MAIN_H))
    tx("FULL TRUTH TABLE — 16 Input Combinations",F_HEAD,C_ACN,W//2,MAIN_Y+24)
    tx("PUMP = T ^ ((S ^ ¬R) v M)",F_SUB,C_AMB,W//2,MAIN_Y+50)
    total_w=sum(COL_W)+len(COL_W)*4
    sx=(W-total_w)//2
    row_h=32; hdr_y=MAIN_Y+68; cont_y=hdr_y+row_h+2
    cx=sx
    for nm,cc,cw in zip(COL_N,COL_C,COL_W):
        rr((cx,hdr_y,cw,row_h),5,(20,28,52),2,cc)
        tx(nm,F_BODY,cc,cx+cw//2,hdr_y+row_h//2)
        cx+=cw+4
    clip=pygame.Rect(0,cont_y,W,H-BOT_H-cont_y-4)
    scr.set_clip(clip)
    max_sc=max(0,16*(row_h+2)-clip.height+8)
    tr_scroll=max(0,min(tr_scroll,max_sc))
    cur=cidx(); row=0
    for sv in range(2):
        for rv in range(2):
            for tv in range(2):
                for mv in range(2):
                    idx=sv*8+rv*4+tv*2+mv
                    g1=not rv; g2=sv and g1; g3=g2 and tv; g4=tv and mv; g5=g3 or g4
                    po=bool(g5)
                    vals=[sv,rv,tv,mv,int(g1),int(g2),int(g3),int(g4),int(g5),"ON" if po else "OFF"]
                    ry=cont_y+row*(row_h+2)-tr_scroll
                    if ry+row_h<cont_y-4 or ry>H-BOT_H: row+=1; continue
                    is_cur=(idx==cur)
                    if is_cur:
                        rr((sx-4,ry,total_w+4,row_h),5,
                           (14,55,24) if po else (48,14,14),3,C_GRN if po else C_RED)
                    else:
                        pygame.draw.rect(scr,(13,15,26) if row%2==0 else (17,20,34),
                                         (sx-4,ry,total_w+4,row_h),border_radius=4)
                    cx=sx
                    for j,(v,cw) in enumerate(zip(vals,COL_W)):
                        if j==9:
                            fc=C_GRN if po else C_MUT
                        else:
                            fc=COL_C[j] if v else C_MUT
                        fnt=F_BTN if (j==9 and is_cur) else F_BODY
                        tx(str(v),fnt,fc,cx+cw//2,ry+row_h//2)
                        cx+=cw+4
                    row+=1
    scr.set_clip(None)
    tx(f"Active input: #{cur} ({cbits()})",F_SUB,C_ACN,W//2,H-BOT_H-18)
# ══════════════════════════════════════════════════════════════════════════════
# TEST CASES
# ══════════════════════════════════════════════════════════════════════════════
def draw_test_cases():
    global tc_scroll
    pygame.draw.rect(scr,(8,10,18),(0,MAIN_Y,W,MAIN_H))
    passed=sum(1 for tc in TC if pump_on(tc[1],tc[2],tc[3],tc[4])==tc[5])
    pct=passed/len(TC)*100
    pc=C_GRN if pct==100 else C_AMB if pct>=70 else C_RED
    tx("TEST CASE SUITE — Verification",F_HEAD,C_ACN,W//2,MAIN_Y+24)
    tx(f"{passed}/{len(TC)} passing — {pct:.0f}%  Input #{cidx()} ({cbits()})",F_SUB,pc,W//2,MAIN_Y+50)
    cols=["ID","S","R","T","M","Expected","Actual","Result","Scenario"]
    cws=[72,42,42,42,42,90,90,92,min(390,W-580)]
    total_w=sum(cws)+len(cws)*4
    sx=(W-total_w)//2
    ccols=[C_MUT,C_AMB,C_BLU,C_GRN,C_PUR,C_WH,C_WH,C_WH,C_MUT]
    row_h=36; hdr_y=MAIN_Y+68; cont_y=hdr_y+row_h+2
    cx=sx
    for nm,cw,cc in zip(cols,cws,ccols):
        rr((cx,hdr_y,cw,row_h),5,(20,28,52),2,cc)
        tx(nm,F_BODY,cc,cx+cw//2,hdr_y+row_h//2)
        cx+=cw+4
    clip=pygame.Rect(0,cont_y,W,H-BOT_H-cont_y-4)
    scr.set_clip(clip)
    max_sc=max(0,len(TC)*(row_h+2)-clip.height+8)
    tc_scroll=max(0,min(tc_scroll,max_sc))
    cs,cr,ct,cm=inp
    for i,tc in enumerate(TC):
        tid,ts,tr,tt,tm,exp,desc=tc
        actual=pump_on(ts,tr,tt,tm)
        ok=actual==exp
        is_cur=(bool(ts)==cs and bool(tr)==cr and bool(tt)==ct and bool(tm)==cm)
        ry=cont_y+i*(row_h+2)-tc_scroll
        if ry+row_h<clip.top-4 or ry>H-BOT_H: continue
        if is_cur:
            rr((sx-4,ry,total_w+4,row_h),5,(13,50,22) if ok else (48,12,12),3,C_GRN if ok else C_RED)
        else:
            pygame.draw.rect(scr,(12,14,25) if i%2==0 else (16,19,32),
                             (sx-4,ry,total_w+4,row_h),border_radius=4)
        cells=[tid,int(ts),int(tr),int(tt),int(tm),
               "ON" if exp else "OFF",
               "ON" if actual else "OFF",
               "PASS" if ok else "FAIL", desc]
        fcs=[C_MUT,
             C_AMB if ts else C_MUT, C_BLU if tr else C_MUT,
             C_GRN if tt else C_MUT, C_PUR if tm else C_MUT,
             C_GRN if exp else C_MUT,
             C_GRN if actual else C_RED,
             C_GRN if ok else C_RED,
             C_WH if is_cur else C_MUT]
        cx=sx
        for v,cw,fc in zip(cells,cws,fcs):
            tx(str(v), F_BTN if is_cur else F_BODY, fc, cx+cw//2, ry+row_h//2)
            cx+=cw+4
    scr.set_clip(None)
    tx(f"Current input #{cidx()} ({cbits()}) — matching rows highlighted",F_SUB,C_ACN,W//2,H-BOT_H-18)
# ══════════════════════════════════════════════════════════════════════════════
# CIRCUIT
# ══════════════════════════════════════════════════════════════════════════════
def draw_circuit():
    pygame.draw.rect(scr,(7,9,17),(0,MAIN_Y,W,MAIN_H))
    s,r,t,m=inp; gs=gsigs(s,r,t,m); po=gs['pump']
    tx("LOGIC CIRCUIT — PUMP = T ^ ((S ^ ¬R) v M)",F_HEAD,C_ACN,W//2,MAIN_Y+26)
    tx("Green wire = HIGH   |   Dark wire = LOW",F_TINY,C_MUT,W//2,MAIN_Y+50)
    MH=MAIN_H-80; centy=MAIN_Y+70+MH//2
    x0=int(W*.07); x1=int(W*.21); x2=int(W*.37)
    x3=int(W*.53); x4=int(W*.67); x5=int(W*.83)
    yS=centy-int(MH*.30); yR=centy-int(MH*.10)
    yT=centy+int(MH*.10); yM=centy+int(MH*.30)
    yA1=(yS+yR)//2; yA2=centy-int(MH*.05)
    yA3=(yT+yM)//2; yOR=centy

    def ibox(bx, by, lbl, col, val):
        rr((bx-58,by-18,116,36),6,(18,22,42),2,col)
        tx(lbl,F_BODY,col,bx-5,by,'r')
        tx("1" if val else "0",F_BTN,C_GRN if val else C_MUT,bx+30,by)
        return bx+58, by

    def obox(bx, by, val):
        col=C_GRN if val else C_RED
        rr((bx,by-30,134,60),10,(12,14,28),3,col)
        tx("PUMP",F_BTN,col,bx+67,by-11)
        tx("ON ✓" if val else "OFF",F_BTN,col,bx+67,by+13)

    se,_=ibox(x0,yS,"S (Soil Dry)",C_AMB,s)
    re_,_=ibox(x0,yR,"R (Rain)",C_BLU,r)
    te,_=ibox(x0,yT,"T (Tank Full)",C_GRN,t)
    me,_=ibox(x0,yM,"M (Manual)",C_PUR,m)
    # NOT R
    wline(re_,yR,x1,yR,r)
    rr((x1,yR-16,54,32),6,C_GNOT,2,C_BLU)
    tx("¬R",F_BODY,C_BLU,x1+27,yR)
    pygame.draw.circle(scr,C_BLU,(x1+54,yR),7)
    nr_x=x1+61
    # AND1: S ^ ¬R
    wline(se,yS,x2,yA1-13,s)
    wline(nr_x,yR,x2,yA1+13,gs['g1'])
    a1x,_=gbox(x2,yA1,"S ^ ¬R",C_AMB,C_GAND,w=90,h=36)
    # AND2: (S^¬R) ^ T → g3
    wline(a1x,yA1,x3,yA2-13,gs['g2'])
    wline(te,yT,x3-24,yT,t)
    wline(x3-24,yT,x3-24,yA2+13,t)
    wline(x3-24,yA2+13,x3,yA2+13,t)
    pygame.draw.circle(scr,C_WON if t else C_WOFF,(te,yT),6)
    a2x,_=gbox(x3,yA2,"S^¬R^T",C_AMB,C_GAND,w=94,h=36)
    # AND3: T ^ M → g4
    wline(te,yT,x2,yA3-13,t)
    wline(me,yM,x2,yA3+13,m)
    a3x,_=gbox(x2,yA3,"T ^ M",C_PUR,C_GPUR,w=82,h=36)
    # OR: g3 v g4
    wline(a2x,yA2,x4,yOR-13,gs['g3'])
    wline(a3x,yA3,x4,yOR+13,gs['g4'])
    orx,_=gbox(x4,yOR,"g3 v g4",C_ACN,C_GOR,w=90,h=36)
    wline(orx,yOR,x5,yOR,gs['g5'])
    obox(x5,yOR,po)
    # Signal trace
    items=[("S",s),("¬R",gs['g1']),("S^¬R",gs['g2']),
           ("S^¬R^T",gs['g3']),("T^M",gs['g4']),("g3vg4",gs['g5']),("PUMP",po)]
    boty=MAIN_Y+MAIN_H-20; seg=(x5+120-x0)//len(items)
    for i,(lbl,val) in enumerate(items):
        tx(f"{lbl}={'1' if val else '0'}",F_TINY,C_GRN if val else C_MUT,x0+i*seg+seg//2,boty)
# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
TABS=[("Scene","scene"),("Truth Table","truth"),
      ("Test Cases","tests"),("Circuit","circuit")]

def draw_tabs():
    pygame.draw.rect(scr,NAV_C,(0,0,W,TAB_H))
    pygame.draw.line(scr,(30,35,65),(0,TAB_H),(W,TAB_H),2)
    tx("IRRIGATION",F_BTN,C_ACN,95,TAB_H//2)
    tw=(W-230)//len(TABS)
    for i,(lbl,v) in enumerate(TABS):
        bx=230+i*tw; bw=tw-6; bh=TAB_H-10
        if view==v:
            rr((bx,5,bw,bh),8,C_ACN)
            tx(lbl,F_BTN,(8,12,28),bx+bw//2,TAB_H//2)
        else:
            rr((bx,5,bw,bh),8,(22,26,52))
            tx(lbl,F_SUB,C_MUT,bx+bw//2,TAB_H//2)

TAB_RECTS=[pygame.Rect(230+i*((W-230)//len(TABS)),5,(W-230)//len(TABS)-6,TAB_H-10)
           for i in range(len(TABS))]
# ══════════════════════════════════════════════════════════════════════════════
# BOTTOM BAR
# ══════════════════════════════════════════════════════════════════════════════
BTN_META=[
    ("Soil Dry",  C_AMB),
    ("Raining",   C_BLU),
    ("Tank Full", C_GRN),
    ("Manual",    C_PUR),
]

def draw_bottom():
    pygame.draw.rect(scr,BOT_C,(0,H-BOT_H,W,BOT_H))
    pygame.draw.line(scr,(30,35,65),(0,H-BOT_H),(W,H-BOT_H),2)
    po=get_pump()
    man=manual_on()
    # ── Row 1: 4 input buttons ────────────────────────────────────────────────
    for i,(rect,(lbl,col)) in enumerate(zip(BTN_RECTS,BTN_META)):
        on=inp[i]
        is_manual_btn=(i==3)
        bg=lerpc(col,(0,0,0),.48) if on else (24,28,56)
        # Manual button glows differently when on
        if is_manual_btn and on:
            for g in range(3,0,-1):
                gc=lerpc(col,(14,16,34),.4+g*.15)
                pygame.draw.rect(scr,gc,(rect.x-g*2,rect.y-g*2,rect.w+g*4,rect.h+g*4),border_radius=12+g*2)
        rr(rect,10,bg,2,col)
        tx(lbl,F_BTN,C_WH,rect.centerx,rect.top+19)
        tx("YES" if on else "NO",F_SUB,col if on else C_MUT,rect.centerx,rect.bottom-14)
    # ── Row 1: RANDOMIZE button ───────────────────────────────────────────────
    rand_disabled=man   # Randomize blocked when Manual is ON
    if rand_disabled:
        rr(RAND_R,10,C_DISA,2,(60,65,90))
        tx("RANDOMIZE",F_BTN,(70,75,100),RAND_R.centerx,RAND_R.centery-8)
        tx("(manual mode)",F_TINY,(60,65,90),RAND_R.centerx,RAND_R.centery+12)
    else:
        rr(RAND_R,10,(22,72,148),2,(60,158,240))
        tx("RANDOMIZE",F_BTN,C_WH,RAND_R.centerx,RAND_R.centery-6)
        tx("S, R, T only",F_TINY,(120,190,255),RAND_R.centerx,RAND_R.centery+14)
    # ── Row 2: Pump status + Combination ─────────────────────────────────────
    pbg=(10,46,20) if po else (46,10,10)
    pc=C_GRN if po else C_RED
    rr(PUMP_R,10,pbg,2,pc)
    pygame.draw.circle(scr,pc,(PUMP_R.left+18,PUMP_R.centery),9)
    dot_inner=lerpc(pc,(255,255,255),.6)
    pygame.draw.circle(scr,dot_inner,(PUMP_R.left+18,PUMP_R.centery),4)
    tx(f"PUMP: {'ON' if po else 'OFF'}",F_HUGE,pc,PUMP_R.centerx+10,PUMP_R.centery)
    rr(COMBO_R,10,(18,20,44),2,C_MUT)
    tx("Combination",F_TINY,C_MUT,COMBO_R.centerx,COMBO_R.top+12)
    tx(f"# {cidx()} ( {cbits()} )",F_BTN,C_WH,COMBO_R.centerx,COMBO_R.bottom-16)
# ══════════════════════════════════════════════════════════════════════════════
# UPDATES & EVENTS
# ══════════════════════════════════════════════════════════════════════════════
def update(dt):
    global timer
    timer+=dt
    for c in clouds:
        c['x']-=c['sp']*dt*20
        if c['x']<-130: c['x']=W+90
    if inp[1]:
        for d in rain_drops:
            d['y']+=d['sp']*dt*25; d['x']-=d['sp']*dt*4
            if d['y']>GRASS_Y:
                d['y']=MAIN_Y-random.randint(0,40)
                d['x']=random.uniform(0,W)

def handle_click(pos):
    global view
    x,y=pos
    # Tabs
    if y < TAB_H:
        for i,(_,v) in enumerate(TABS):
            if TAB_RECTS[i].collidepoint(pos):
                view=v; return
    # Bottom bar
    if y > H-BOT_H:
        # Input buttons (always clickable)
        for i,r in enumerate(BTN_RECTS):
            if r.collidepoint(pos):
                inp[i]=not inp[i]
                return
        # Randomize — only when Manual is OFF
        if RAND_R.collidepoint(pos):
            if not manual_on():
                # Randomize only S, R, T — M stays OFF
                inp[0]=random.choice([True,False])
                inp[1]=random.choice([True,False])
                inp[2]=random.choice([True,False])
                inp[3]=False
            return

def handle_scroll(dy, pos):
    global tr_scroll, tc_scroll
    if MAIN_Y < pos[1] < H-BOT_H:
        if view=='truth': tr_scroll=max(0,tr_scroll-dy*28)
        if view=='tests': tc_scroll=max(0,tc_scroll-dy*28)
# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════
def main():
    while True:
        dt=clk.tick(60)/1000.0
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
            elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                handle_click(e.pos)
            elif e.type==pygame.MOUSEWHEEL:
                handle_scroll(e.y, pygame.mouse.get_pos())
        update(dt)
        if view=='scene':   draw_scene()
        elif view=='truth': draw_truth_table()
        elif view=='tests': draw_test_cases()
        elif view=='circuit': draw_circuit()
        draw_tabs()
        draw_bottom()
        pygame.display.flip()

if __name__=="__main__":
    main()
