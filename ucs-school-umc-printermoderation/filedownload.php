<?php

//$basedir = "/var/cache/cups-pdf/";
$basedir = "/var/cache/printermoderation/";

//print "\n<br />1 " . var_dump ($_GET['filename']);
//print "\n<br />2 " . var_dump (!isset ($_GET['filename']));
//print "\n<br />3 " . var_dump (ereg ("\.\.\/", $_GET['filename']));
//print "\n<br />4 " . var_dump (!ereg ("\.pdf$", $_GET['filename']));
//print "\n<br />5 " . var_dump ($basedir . $_GET['filename']);
//print "\n<br />6 " . var_dump (!file_exists ($basedir . $_GET['filename']));

if (!isset ($_GET['filename']) || ereg ("\.\.\/", $_GET['filename']) ||
	!ereg ("\.pdf$", $_GET['filename']) || !is_file ($basedir . $_GET['filename']))
{
	header("HTTP/1.0 404 Not Found");
	exit;
}

$filename = $basedir . $_GET['filename'];

// Wir werden eine PDF Datei ausgeben
header('Content-type: application/pdf');

// Es wird downloaded.pdf benannt
header('Content-Disposition: attachment; filename=' . basename ($filename));

echo file_get_contents($filename);

?>
