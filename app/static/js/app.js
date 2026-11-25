document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  if (!toggle || !sidebar) return;
  const closeMenu = () => {
    sidebar.classList.remove("open");
    document.body.classList.remove("menu-open");
    toggle.setAttribute("aria-expanded", "false");
  };
  const openMenu = () => {
    sidebar.classList.add("open");
    document.body.classList.add("menu-open");
    toggle.setAttribute("aria-expanded", "true");
  };
  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    sidebar.classList.contains("open") ? closeMenu() : openMenu();
  });
  document.addEventListener("click", (event) => {
    if (window.innerWidth <= 780 && sidebar.classList.contains("open") &&
        !sidebar.contains(event.target) && !toggle.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  sidebar.querySelectorAll("a.nav-link").forEach(link => link.addEventListener("click", closeMenu));
  window.addEventListener("resize", () => { if (window.innerWidth > 780) closeMenu(); });
});

document.addEventListener("DOMContentLoaded",()=>{const input=document.getElementById("studentMatricule"),btn=document.getElementById("findStudent"),box=document.getElementById("studentResult");if(!input||!btn||!box)return;const search=async()=>{const code=input.value.trim();if(!code)return;box.hidden=false;box.textContent="Recherche…";try{const response=await fetch("/modules/api/etudiants/"+encodeURIComponent(code));if(!response.ok)throw new Error("Aucun étudiant trouvé avec ce matricule.");const s=await response.json();const fields=[["Nom complet",s.full_name],["Matricule",s.matricule],["E-mail",s.email],["Option",s.option],["Mention",s.mention],["Promotion",s.promotion],["Sujet",s.subject],["Programme",s.program],["Niveau",s.level],["Tuteur",s.tutor],["Codirecteur",s.codirector],["Statut",s.status]];box.innerHTML=fields.map(x=>"<div><small>"+x[0]+"</small><b></b></div>").join("");box.querySelectorAll("b").forEach((el,i)=>el.textContent=fields[i][1]||"—");}catch(error){box.textContent=error.message;}};btn.addEventListener("click",search);input.addEventListener("change",search);input.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();search();}});});

document.addEventListener("DOMContentLoaded",()=>{const input=document.getElementById("password"),button=document.getElementById("togglePassword");if(!input||!button)return;button.addEventListener("click",()=>{const visible=input.type==="password";input.type=visible?"text":"password";button.setAttribute("aria-pressed",String(visible));button.setAttribute("aria-label",visible?"Masquer le mot de passe":"Afficher le mot de passe");});});

(() => {
  const hideLoader = () => {
    const loader = document.getElementById('appLoading');
    const bar = document.getElementById('globalProgress');
    if (loader) { loader.classList.remove('is-visible'); loader.classList.add('is-hidden'); }
    if (bar) { bar.classList.remove('is-running'); bar.classList.add('is-complete'); window.setTimeout(() => bar.classList.remove('is-complete'), 250); }
  };
  document.addEventListener('DOMContentLoaded', () => {
    hideLoader();
    // La navigation mobile conserve le contenu visible : seule la barre fine progresse.
    document.querySelectorAll('a[href]').forEach((link) => {
      link.addEventListener('click', (event) => {
        const href = link.getAttribute('href') || '';
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.button === 1 ||
            link.target === '_blank' || link.hasAttribute('download') ||
            href.startsWith('#') || href.startsWith('javascript:')) return;
        const bar = document.getElementById('globalProgress');
        if (bar) { bar.classList.remove('is-complete'); bar.classList.add('is-running'); }
      });
    });
    document.querySelectorAll('form').forEach((form) => form.addEventListener('submit', () => {
      const bar = document.getElementById('globalProgress');
      if (bar) bar.classList.add('is-running');
    }));
    window.setTimeout(hideLoader, 1800);
  });
  window.addEventListener('pageshow', hideLoader);
  window.addEventListener('load', hideLoader);
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
