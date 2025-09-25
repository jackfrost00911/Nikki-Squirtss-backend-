<?php
require 'config.php';
require 'PHPMailer/PHPMailer.php';
require 'PHPMailer/SMTP.php';
require 'PHPMailer/Exception.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

function sendAlert($subject, $body) {
    $mail = new PHPMailer(true);
    try {
        // SMTP configuration
        $mail->isSMTP();
        $mail->Host = 'smtp.gmail.com';
        $mail->SMTPAuth = true;
        $mail->Username = 'jackfrost00911@gmail.com';
        $mail->Password = 'GOKILLURSELF!';
        $mail->SMTPSecure = 'tls';
        $mail->Port = 587;

        // Email headers
        $mail->setFrom(GMAIL_USER, FROM_NAME);
        $mail->addAddress(ALERT_EMAIL);

        $mail->isHTML(false); // Set email format to plain text
        $mail->Subject = $subject;
        $mail->Body    = $body;

        $mail->send();
        echo 'Alert email sent successfully.';
    } catch (Exception $e) {
        echo "Message could not be sent. Mailer Error: {$mail->ErrorInfo}";
    }
}

// Example use:
sendAlert(
    'Test Alert',
    "This is a test notification from Nikki’s Booking Desk."
);
