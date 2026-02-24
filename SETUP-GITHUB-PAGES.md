# Publication sur interpretive-governance.org (GitHub Pages)

Objectif : publier un site statique **sans** Jekyll, depuis la branche `main`.

## 1) Activer GitHub Pages

1. Dans le dépôt : **Settings → Pages**
2. Dans “Build and deployment” :
   - Source : **Deploy from a branch**
   - Branch : `main`
   - Folder : `/ (root)`

Référence : https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

## 2) Domaine custom

Deux approches (les deux fonctionnent) :

- via l’UI GitHub : Settings → Pages → “Custom domain”
- via un fichier `CNAME` dans la racine publiée (ce dépôt en contient déjà un)

Référence : https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site  
Dépannage : https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages

## 3) HTTPS

Activer “Enforce HTTPS” quand l’option devient disponible.

Référence : https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https

## 4) Désactiver Jekyll

Le fichier `.nojekyll` est présent. Il évite des surprises (répertoires commençant par `_`, `.well-known`, etc.).

Référence (historique) : https://github.blog/news-insights/bypassing-jekyll-on-github-pages/
