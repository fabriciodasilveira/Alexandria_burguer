# FROM nginx:alpine
# COPY dist /usr/share/nginx/html
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]

FROM nginx:alpine

# Copia os ficheiros do site (o seu index.html e outros)
COPY dist /usr/share/nginx/html

# Copia a nossa configuração personalizada para o Nginx
# e substitui a configuração padrão
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY .htpasswd /etc/nginx/.htpasswd

EXPOSE 8081
CMD ["nginx", "-g", "daemon off;"]