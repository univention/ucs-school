# Release instructions for the app "UCS@school Veyon Proxy"

1. QA app in test appcenter
2. ``ssh omar``
3. ``cd /mnt/omar/vmwares/mirror/appcenter``
4. ``./copy_from_appcenter.test.sh 4.4``
5. ``./copy_from_appcenter.test.sh 4.4 ucsschool-veyon-proxy_20201207103635``
6. When asked ``DockerImage does not follow the format...`` choose ``1``.
7. ``sudo update_mirror.sh -v appcenter``
8. Send an internal announcement mail. Text see ``README_Releases.md``.
