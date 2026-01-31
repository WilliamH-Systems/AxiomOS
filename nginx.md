```
sudo nano /etc/nginx/sites-available/axiomos
sudo ln -s /etc/nginx/sites-available/axiomos /etc/nginx/sites-enabled/
sudo nginx -t
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```
sudo service nginx restart
```

*Make sure you have postgresql and redis installed and started!*