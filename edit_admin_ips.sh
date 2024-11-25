#!/bin/bash

filename=".env"

if [ "$1" = "-h" ] || [ "$1" = "--help" ] || ([ "$1" != "add" ] && [ "$1" != "remove" ] && [ "$1" != "show" ])
  then
    echo "Usage: $0 COMMAND [OPTIONS] [IP]
        Display or edit ip list for admin restrictions
        Example: $0 add 192.168.0.1
                         $0 show
                         $0 remove -r 192.168.0.0/24
                         $0 add -r 192.168.0.0

        COMMAND:
                The available commands are add, remove and show

        OPTIONS:
                -r, --range             Specify it's IP range and not a single IP
                -f, --filename          Specify path to env file
                -n, --no-reset          Don't reset app service after editing
                -t, --test              Don't change file or reset the service, just show the changes"
    exit 1
fi

ip="${!#}"
new_ips=""
setting_key="DJANGO_ALLOWED_ADMIN_IPS"
is_test=0

if [ "$1" = "add" ] || [ "$1" = "remove" ]; then
        reset_app=1
else
        reset_app=0
fi

for (( i=2; i <= "$#"; i++ )); do

        if [ "${!i}" = "-r" ] || [ "${!i}" = "--range" ]; then
                ip_without_last_seg="${ip%.*}"
                ip="${ip_without_last_seg}.0/24"
                setting_key="DJANGO_ALLOWED_ADMIN_IP_RANGES"
        fi
        if [ "${!i}" = "-f" ]; then
              filename="${!i}"
        fi
        if [ "${!i}" = "-n" ] || [ "${!i}" = "--no-reset" ]; then
                reset_app=0
        fi
        if [ "${!i}" = "-t" ] || [ "${!i}" = "--test" ]; then
                is_test=1
        fi
done

if [ ! -f "$filename" ]; then
    echo "$filename does not exist. Exiting program"
        exit 1
fi

ips=$(grep "^$setting_key=" $filename | cut -d'=' -f2)
IFS=',' read -r -a ip_array <<< $ips

if [ "$1" = "add" ]; then
        ip_array[${#ip_array[@]}]="$ip"
        for value in "${ip_array[@]}"
        do
                new_ips="${new_ips}${value},"
        done
        new_ips="${new_ips%?}"
fi

if [ "$1" = "remove" ]; then
        found=0
        for value in "${ip_array[@]}"
        do
                if [ "$value" = "$ip" ]
                then
                        found=1
                else
                        new_ips="${new_ips}${value},"
                fi
        done
        if [ $found -eq 0 ]
        then
                echo Could not find IP "$ip" to remove
                exit 1
        fi
        new_ips="${new_ips%?}"
fi

if [ "$1" = "show" ]; then
        echo "Current IPs: ${ip_array[@]}"
fi

new_ips="${new_ips}"

if [ "$1" = "add" ] || [ "$1" = "remove" ]; then
        if [ $is_test -eq 0 ]; then
                sed -i "s/$setting_key=.*/$setting_key=${new_ips//\//\\/}/" $filename
                echo Changed Settings

                if [ $reset_app -eq 1 ]; then
                        sudo docker compose -f docker-compose-deploy-temp-volumes.yml down app
                        sudo docker compose -f docker-compose-deploy-temp-volumes.yml up -d app
                        echo Service Restarted
                fi

        else
                echo "$ips" ">>" "$new_ips"
        fi
fi
