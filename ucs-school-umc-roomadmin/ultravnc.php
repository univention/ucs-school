<?php

$fn = "/usr/share/univention-management-console/www/ultravnc.vnc";

$HOSTNAME = "127.0.0.1";
if (isset($_GET['hostname'])) {
  $HOSTNAME = $_GET['hostname'];
}

// Wir werden eine PDF Datei ausgeben
header('Content-type: application/binary');

// Es wird downloaded.pdf benannt
header('Content-Disposition: attachment; filename=' . $HOSTNAME . '.vnc');

$content = file_get_contents($fn);

$content = str_replace("@%@HOSTNAME@%@", $HOSTNAME, $content);

if (isset($_GET['port'])) {
  $PORT = $_GET['port'];
} else {
	$PORT = "5900";
}
$content = str_replace("@%@PORT@%@", $PORT, $content);

echo $content;

?>
