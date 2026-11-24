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

document.addEventListener("DOMContentLoaded", () => {
  const bar = document.getElementById("globalProgress");
  if (!bar) return;
  const start = () => { bar.classList.add("is-running"); };
  document.querySelectorAll("a[href], form").forEach((el) => {
    el.addEventListener("click", (event) => {
      if (el.tagName === "A" && (event.ctrlKey || event.metaKey || el.target === "_blank")) return;
      start();
    });
    if (el.tagName === "FORM") el.addEventListener("submit", start);
  });
  window.addEventListener("pageshow", () => bar.classList.remove("is-running"));
});
