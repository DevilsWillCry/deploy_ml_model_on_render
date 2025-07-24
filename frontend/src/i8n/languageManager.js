// src/i18n/languageManager.js
import { translations } from "./translations";
let currentLanguage = "es";

function getTranslation(lang, array) {
  array.forEach((element) => {
    const key = element.getAttribute("data-i8n");
    element.textContent = translations[lang][key];
  });
}

export function updateLanguage() {
  const inputLanguage = document.getElementById("language-toggle");
  if (!inputLanguage) return;

  //Check the current language from local storage
  if (localStorage.getItem("language") === "en") {
    inputLanguage.checked = true;
    getTranslation("en", document.querySelectorAll("[data-i8n]"));
  } else {
    inputLanguage.checked = false;
  }

  inputLanguage.addEventListener("change", () => {
    currentLanguage = inputLanguage.checked ? "en" : "es";

    getTranslation(currentLanguage, document.querySelectorAll("[data-i8n]"));

    //Save to local storage
    localStorage.setItem("language", currentLanguage);
  });
}
