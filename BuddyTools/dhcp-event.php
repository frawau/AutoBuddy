#!/usr/bin/php
<?php
/*
 *  Example of HOWTO: PHP TCP Server/Client with SSL Encryption using Streams
 *  Client side Script
 *
 *  Website : http://blog.leenix.co.uk/2011/05/howto-php-tcp-serverclient-with-ssl.html
 #  Adapted to AutoBuddy by François Wautier
 */

$ip="<AUTOBUDDYHOST/>";     //Set the TCP IP Address to connect too
$port="<AUTOBUDDYPORT/>";        //Set the TCP PORT to connect too
$credential="<AUTOBUDDYCREDENTIAL/>";       //Credentials

$macaddr=$argv[2];
$ipaddr=$argv[3];
$hostname=$argv[4];

if ( $argv[1] == 'add' ) {
    $onlinestatus='online';
} else if  ( $argv[1] == 'del' ) {
    $onlinestatus='offline';
} else if  ( $argv[1] == 'old' ) {
    $onlinestatus='online';
} else {
    exit;
}

//Connect to Server
$socket = stream_socket_client("tcp://{$ip}:{$port}", $errno, $errstr, 30);

if($socket) {
 //Start SSL
 stream_context_set_option($socket, 'ssl', 'verify_peer', false); 
 stream_context_set_option($socket, 'ssl', 'verify_peer_name', false); 
 stream_set_blocking ($socket, true);
 stream_socket_enable_crypto ($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT);
 //stream_set_blocking ($socket, false);
 $content = array('credential' => $credential, 'subject' => 'device');
 $msg = array('subject' => 'control', 'content_type' => 'authenticate', 'content' => $content);
 
 fwrite($socket,json_encode($msg) );
 fflush($socket);
 /* Send the event */
 $value = array ( 'status' => $onlinestatus, 'ip' => $ipaddr, 'hostname' => $hostname, 'mac' => $macaddr );
 $content = array('event' => 'dhcp', 'value' => $value, 'target' => 'device.mac-'.$macaddr);
 $msg = array('subject' => 'device', 'content_type' => 'event', 'content' => $content);

 //Send a command
 fwrite($socket,json_encode($msg) );
 fflush($socket);
}

 //close connection
 fclose($socket);

?>