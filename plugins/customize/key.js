export default class KeyPlugin {
  constructor() {
    const ID="keystroke-ui";
    const old=document.getElementById(ID);
    if(old){ old.remove(); window.__ks_cleanup__?.(); return; }

    const getLayout=()=>{
      let l=["d","f","j","k"];
      try{
        const r=localStorage.getItem("settings");
        if(!r) return l;
        const s=JSON.parse(r),ks=s?.keyboardSettings;
        if(!ks) return l;
        const g=a=>Array.isArray(a)&&a[0]?a[0].toLowerCase():null;
        const a=g(ks.ka_l),b=g(ks.don_l),c=g(ks.don_r),d=g(ks.ka_r);
        if(a&&b&&c&&d) l=[a,b,c,d];
      }catch(e){}
      return l;
    };

    let map={},box=null,cur=[];

    const build=l=>{
      cur=l.slice();
      if(box) box.remove();
      box=document.createElement("div");
      box.id=ID;
      box.style.position="fixed";
      box.style.right="20px";
      box.style.bottom="20px";
      box.style.display="grid";
      box.style.gridTemplateColumns="repeat(4,50px)";
      box.style.gap="5px";
      box.style.zIndex="999999";
      map={};
      l.forEach(k=>{
        const e=document.createElement("div");
        e.textContent=k.toUpperCase();
        e.style.width="50px";
        e.style.height="50px";
        e.style.display="flex";
        e.style.alignItems="center";
        e.style.justifyContent="center";
        e.style.background="rgba(0,0,0,0.6)";
        e.style.color="#fff";
        e.style.borderRadius="8px";
        e.style.fontWeight="bold";
        box.appendChild(e);
        map[k]=e;
      });
      document.body.appendChild(box);
    };

    build(getLayout());

    const d=e=>{const k=e.key.toLowerCase();if(map[k]){map[k].style.background="#00ff88";map[k].style.transform="scale(0.9)";}};
    const u=e=>{const k=e.key.toLowerCase();if(map[k]){map[k].style.background="rgba(0,0,0,0.6)";map[k].style.transform="scale(1)";}};

    window.addEventListener("keydown",d);
    window.addEventListener("keyup",u);
  }
}
