document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (event) => {
      if (window.innerWidth <= 760 && sidebar.classList.contains("open") &&
          !sidebar.contains(event.target) && !toggle.contains(event.target)) {
        sidebar.classList.remove("open");
      }
    });
  }
});

document.addEventListener("DOMContentLoaded",()=>{const input=document.getElementById("studentMatricule"),btn=document.getElementById("findStudent"),box=document.getElementById("studentResult");if(!input||!btn||!box)return;const search=async()=>{const code=input.value.trim();if(!code)return;box.hidden=false;box.textContent="Recherche…";try{const response=await fetch("/modules/api/etudiants/"+encodeURIComponent(code));if(!response.ok)throw new Error("Aucun étudiant trouvé avec ce matricule.");const s=await response.json();const fields=[["Nom complet",s.full_name],["Matricule",s.matricule],["E-mail",s.email],["Option",s.option],["Mention",s.mention],["Promotion",s.promotion],["Sujet",s.subject],["Programme",s.program],["Niveau",s.level],["Directeur",s.tutor],["Codirecteur",s.codirector],["Statut",s.status]];box.innerHTML=fields.map(x=>"<div><small>"+x[0]+"</small><b></b></div>").join("");box.querySelectorAll("b").forEach((el,i)=>el.textContent=fields[i][1]||"—");}catch(error){box.textContent=error.message;}};btn.addEventListener("click",search);input.addEventListener("change",search);input.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();search();}});});

document.addEventListener("DOMContentLoaded",()=>{const input=document.getElementById("password"),button=document.getElementById("togglePassword");if(!input||!button)return;button.addEventListener("click",()=>{const visible=input.type==="password";input.type=visible?"text":"password";button.setAttribute("aria-pressed",String(visible));button.setAttribute("aria-label",visible?"Masquer le mot de passe":"Afficher le mot de passe");});});

(() => {
  const showLoader = () => {
    const loader = document.getElementById("appLoading");
    const bar = document.getElementById("globalProgress");
    if (loader) { loader.classList.remove("is-hidden"); loader.classList.add("is-visible"); }
    if (bar) bar.classList.add("is-running");
  };
  const hideLoader = () => {
    const loader = document.getElementById("appLoading");
    const bar = document.getElementById("globalProgress");
    if (loader) { loader.classList.remove("is-visible"); loader.classList.add("is-hidden"); }
    if (bar) bar.classList.remove("is-running");
  };
  document.addEventListener("DOMContentLoaded", () => {
    window.setTimeout(hideLoader, 220);
    document.querySelectorAll("a[href]").forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.button === 1 ||
            link.target === "_blank" || link.hasAttribute("download") ||
            link.getAttribute("href").startsWith("#") ||
            link.getAttribute("href").startsWith("javascript:")) return;
        showLoader();
      });
    });
    document.querySelectorAll("form").forEach((form) => {
      form.addEventListener("submit", () => showLoader());
    });
  });
  window.addEventListener("pageshow", hideLoader);
})();


/* Présence : actualise le statut en ligne pendant la session authentifiée. */
document.addEventListener("DOMContentLoaded", () => {
  const token = document.querySelector('meta[name="csrf-token"]')?.content;
  if (!token || !document.querySelector(".profile-entry")) return;
  const ping = () => fetch("/auth/presence", {method:"POST", headers:{"X-CSRFToken":token}, credentials:"same-origin", keepalive:true}).catch(() => {});
  ping();
  window.setInterval(ping, 60000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) ping(); });
});


/* Sur la page profil, toujours revenir au début après un enregistrement/rechargement.
   Certains navigateurs mobiles restaurent l'ancienne position de défilement et
   donnent l'impression qu'un grand bloc vide précède le contenu. */
(() => {
  const resetProfileScroll = () => {
    if (window.location.pathname === "/auth/profil") {
      window.scrollTo({top: 0, left: 0, behavior: "instant"});
    }
  };
  document.addEventListener("DOMContentLoaded", () => {
    resetProfileScroll();
    requestAnimationFrame(resetProfileScroll);
  });
  window.addEventListener("pageshow", resetProfileScroll);
})();
