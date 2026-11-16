#!/usr/bin/env python3
"""Draw an illustrated replay from export_demo.cjs; requires Pillow + imageio-ffmpeg.
No browser screenshot is synthesized or altered. The paths and scores are actual
outputs of the shipped rules and trained neural planner, for one disclosed round.
"""
from pathlib import Path
import json, math, os, subprocess
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/assets'; OUT.mkdir(exist_ok=True,parents=True)
DATA=json.loads((ROOT/'promotion/demo-replay.json').read_text())
FONT=Path(os.environ.get('ORBIT_MEDIA_FONT','/System/Library/Fonts/Supplemental/Arial.ttf'))
BOLD=Path(os.environ.get('ORBIT_MEDIA_BOLD','/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
CJK=Path(os.environ.get('ORBIT_MEDIA_CJK','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
BG='#0B101C'; PANEL='#121C2D'; TEXT='#F1F4FA'; MUTED='#A7B4C9'; PURPLE='#B6A0FF'; MINT='#77E6CD'; LINE='#2B3950'
CACHE={}
def font(size,bold=False,zh=False):
 key=(size,bold,zh)
 if key not in CACHE: CACHE[key]=ImageFont.truetype(str(CJK if zh else BOLD if bold else FONT),size)
 return CACHE[key]
def txt(d,xy,s,size=22,color=TEXT,bold=False,zh=False):
 d.text(xy,s,font=font(size,bold,zh),fill=color)
def box(d,r,fill=PANEL,outline=None,radius=18,width=1):
 d.rounded_rectangle(r,radius=radius,fill=fill,outline=outline,width=width)
def linepath(d,path,bounds,color,width=4,progress=1):
 x,y,w,h=bounds
 points=[(x+a*w,y+b*h) for a,b in path]
 p=max(0,min(1,progress))*(len(points)-1); i=min(len(points)-2,int(p)); frac=p-i
 current=(points[i][0]+(points[i+1][0]-points[i][0])*frac,points[i][1]+(points[i+1][1]-points[i][1])*frac)
 shown=points[:i+1]+[current]
 if progress>0: d.line(shown,fill=color,width=width,joint='curve')
 d.ellipse((current[0]-7,current[1]-7,current[0]+7,current[1]+7),fill=color)
 return current

def field(d,bounds,player=0,model=0,labels=True):
 x,y,w,h=bounds
 box(d,(x,y,x+w,y+h),'#0E1726',LINE,12)
 for n in range(1,10):
  d.line((x+n*w/10,y+8,x+n*w/10,y+h-8),fill='#1D293E',width=1)
  d.line((x+8,y+n*h/10,x+w-8,y+n*h/10),fill='#1D293E',width=1)
 for p in [DATA['previous'],DATA['start']]:
  px=x+p[0]*w; py=y+p[1]*h
  d.ellipse((px-9,py-9,px+9,py+9),outline=MUTED,width=2)
 gx=x+DATA['goal'][0]*w; gy=y+DATA['goal'][1]*h
 rx=DATA['hitRadius']*w; ry=DATA['hitRadius']*h
 d.ellipse((gx-rx,gy-ry,gx+rx,gy+ry),fill='#273048',outline=TEXT,width=2)
 d.line((gx-5,gy,gx+5,gy),fill=TEXT,width=2);d.line((gx,gy-5,gx,gy+5),fill=TEXT,width=2)
 if labels: txt(d,(gx-25,gy-ry-27),'GOAL',15,MUTED,True)
 if player>0: linepath(d,DATA['player']['path'],bounds,MINT,4,player)
 if model>0: linepath(d,DATA['model']['path'],bounds,PURPLE,4,model)

def poster(lang):
 im=Image.new('RGB',(1280,640),BG);d=ImageDraw.Draw(im);zh=lang=='zh'
 # restrained orbit motif, behind the content
 for k in range(3):d.ellipse((920-k*25,-210-k*25,1430+k*25,290+k*25),outline='#202640',width=2)
 txt(d,(60,36),'ORBIT',36,TEXT,True);txt(d,(200,49),'TINY JEPA LAB',15,MUTED,True)
 copy={
 'en':('A PLAYABLE WORLD-MODEL DEMO',['What happens','if I do this?'],['A tiny AI predicts the effects of actions.','Choose your plan. See what happens.'],'Play in your browser','5 daily rounds · No sign-up to play','ACTUAL REPLAY','YOU','AI'),
 'ru':('ИГРОВОЕ ДЕМО МОДЕЛИ МИРА',['Что случится,','если сделать так?'],['Нейросеть прогнозирует последствия действий.','Выбери свой план и сравни результат.'],'Играть в браузере','5 раундов · Без регистрации для игры','РЕАЛЬНЫЙ РАУНД','ТЫ','AI'),
 'zh':('可以亲手体验的世界模型演示',['如果这样做，','会发生什么？'],['小型神经网络预测动作的结果。','选择你的计划，再比较实际结果。'],'在浏览器中体验','5 个回合 · 游玩无需注册','实际回放','你','AI')
 }[lang]
 txt(d,(64,137),copy[0],17,PURPLE,True,zh)
 for j,s in enumerate(copy[1]): txt(d,(60,184+j*76),s,54 if lang=='ru' else 62,TEXT,True,zh)
 for j,s in enumerate(copy[2]): txt(d,(64,369+j*34),s,21 if lang=='ru' else 23,MUTED,False,zh)
 box(d,(64,468,370,524),MINT,radius=28);txt(d,(87,480),copy[3],23,'#0B2926',True,zh)
 txt(d,(64,553),copy[4],19,MUTED,False,zh)
 box(d,(724,114,1220,528),PANEL,LINE,24)
 txt(d,(752,137),copy[5],15,MUTED,True,zh)
 field(d,(752,185,440,228),1,1,False)
 txt(d,(754,446),copy[6]+'  '+str(DATA['player']['score']),25,MINT,True,zh)
 txt(d,(978,446),copy[7]+'  '+str(DATA['model']['score']),25,PURPLE,True,zh)
 txt(d,(756,488),'OBSERVE  →  PREDICT  →  PLAN',13,MUTED,True)
 txt(d,(728,558),'artandrew.github.io/tiny-jepa-lab',18,MUTED)
 im.save(OUT/f'orbit-social-{lang}.png',optimize=True)
 return im

def chip(d,x,y,label,active=False):
 box(d,(x,y,x+92,y+45),'#213B3A' if active else '#182237',MINT if active else LINE,10)
 f=font(16,True);width=d.textlength(label,font=f)
 txt(d,(x+(92-width)/2,y+12),label,16,MINT if active else MUTED,True)

def frame(t):
 im=Image.new('RGB',(1000,560),BG);d=ImageDraw.Draw(im)
 txt(d,(34,24),'ORBIT',29,TEXT,True);txt(d,(158,34),'A WORLD MODEL YOU CAN PLAY',14,PURPLE,True)
 txt(d,(36,76),'Can you plan better than a tiny neural network?',29,TEXT,True)
 # Three phases: user input, model selection, observed outcome.
 stage=0 if t<4.5 else 1 if t<7 else 2
 names=['1  CHOOSE ACTIONS','2  AI PREDICTS & PLANS','3  COMPARE RESULTS']
 for j,label in enumerate(names):
  x=36+j*318
  box(d,(x,130,x+300,167),'#2A2442' if j==stage else PANEL,radius=8)
  txt(d,(x+13,140),label,15,PURPLE if j==stage else MUTED,True)
 box(d,(36,185,348,454),PANEL,LINE,16)
 if stage==0:
  txt(d,(54,201),'YOUR PLAN',16,MINT,True)
  for j in range(3):
   txt(d,(54,234+j*62),'ACTION '+str(j+1),12,MUTED,True)
   for k,label in enumerate(['Left','No push','Right']):chip(d,54+k*92,252+j*62,label,k==1 and t>(j+1)*.45)
 elif stage==1:
  txt(d,(54,205),'THE WORLD MODEL',16,PURPLE,True)
  for j,label in enumerate(['Observes two images','Predicts 27 possible plans','Chooses a plan for the goal']):
   txt(d,(54,250+j*43),label,17,TEXT)
  acts=['Left' if a<0 else 'Right' if a>0 else 'No push' for a in DATA['model']['actions']]
  for k,label in enumerate(acts):chip(d,54+k*92,387,label,True)
 else:
  txt(d,(54,208),'ACTUAL RESULTS',16,MUTED,True)
  txt(d,(54,253),'YOU',16,MINT,True);txt(d,(54,277),str(DATA['player']['score']),51,MINT,True)
  txt(d,(201,253),'AI',16,PURPLE,True);txt(d,(201,277),str(DATA['model']['score']),51,PURPLE,True)
  txt(d,(54,364),'Closer to the goal = more points',16,MUTED)
  txt(d,(54,397),'Try your own three actions.',17,TEXT,True)
 player=max(0,min(1,(t-2)/2.4))
 model=max(0,min(1,(t-7)/2.4))
 field(d,(370,185,594,269),player,model)
 # Bottom area is kept still enough to read in every phase.
 caption='Choose your actions before the ball moves.' if stage==0 else 'A learned prediction helps the AI choose.' if stage==1 else 'The simulator reveals what actually happens.'
 txt(d,(36,475),caption,21,TEXT,True)
 txt(d,(36,519),'Illustrated real replay · One example, not a benchmark',13,MUTED)
 txt(d,(643,519),'artandrew.github.io/tiny-jepa-lab',15,MINT,True)
 return im

if __name__=='__main__':
 for lang in ['en','ru','zh']: poster(lang)
 fps=10; frames=[frame(i/fps) for i in range(13*fps)]
 frames[100].save(OUT/'orbit-demo-poster.png',optimize=True)
 # Fixed palette stabilizes the GIF without altering the underlying replay.
 palette=frames[100].quantize(colors=96)
 indexed=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
 indexed[0].save(OUT/'orbit-demo.gif',save_all=True,append_images=indexed[1:],duration=100,loop=0,optimize=True,disposal=1)
 ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
 cmd=[ffmpeg,'-y','-f','rawvideo','-pix_fmt','rgb24','-s','1000x560','-r',str(fps),'-i','-','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'orbit-demo.mp4')]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 for f in frames:p.stdin.write(f.tobytes())
 p.stdin.close();err=p.stderr.read();assert p.wait()==0,err.decode()
 for f in sorted(OUT.glob('orbit-*')):print(f.name,f.stat().st_size)
