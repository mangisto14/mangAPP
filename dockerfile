# משתמשים בשרת Nginx קליל
FROM nginx:alpine

# מעתיקים את כל הקבצים בתיקייה (כולל ה-HTML) לתיקיית התצוגה של השרת
COPY . /usr/share/nginx/html

# חשיפת פורט 80 (הסטנדרט של Nginx)
EXPOSE 80
