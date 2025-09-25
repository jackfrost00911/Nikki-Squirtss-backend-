 
<?php
require 'config.php';
require 'PHPMailer/PHPMailer.php';
require 'PHPMailer/SMTP.php';
require 'PHPMailer/Exception.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name     = htmlspecialchars($_POST['name'] ?? '');
    $email    = htmlspecialchars($_POST['email'] ?? '');
    $phone    = htmlspecialchars($_POST['phone'] ?? '');
    $service  = htmlspecialchars($_POST['service'] ?? '');
    $datetime = htmlspecialchars($_POST['datetime'] ?? '');
    $location = htmlspecialchars($_POST['location'] ?? '');
    $notes    = htmlspecialchars($_POST['notes'] ?? '');

    $subject = "New Booking: $name";
    $body = "A new booking was submitted:\n\n";
    $body .= "Name: $name\n";
    $body .= "Email: $email\n";
    $body .= "Phone: $phone\n";
    $body .= "Service: $service\n";
    $body .= "Date & Time: $datetime\n";
    $body .= "Location: $location\n";
    $body .= "Notes: $notes\n";

    $mail = new PHPMailer(true);
    try {
        $mail->isSMTP();
        $mail->Host = 'smtp.gmail.com';
        $mail->SMTPAuth = true;
        $mail->Username = 'jackfrost00911@gmail.com';
        $mail->Password = 'GOKILLURSELF!';
        $mail->SMTPSecure = 'tls';
        $mail->Port = 587;

        $mail->setFrom(GMAIL_USER, FROM_NAME);
        $mail->addAddress(ALERT_EMAIL);

        $mail->isHTML(false);
        $mail->Subject = $subject;
        $mail->Body    = $body;

        $mail->send();
        echo "<p>Thank you! Your booking request has been sent.</p>";
    } catch (Exception $e) {
        echo "<p>Mailer Error: {$mail->ErrorInfo}</p>";
    }
} else {
    ?>
    <!DOCTYPE html>
    <html>
    <head><title>Booking Form</title></head>
    <body>
    <form method="post" action="">
      <label>Name:</label><br>
      <input type="text" name="name" required><br>
      <label>Email:</label><br>
      <input type="email" name="email" required><br>
      <label>Phone:</label><br>
      <input type="text" name="phone"><br>
      <label>Service:</label><br>
      <input type="text" name="service" required><br>
      <label>Date & Time:</label><br>
      <input type="datetime-local" name="datetime" required><br>
      <label>Location:</label><br>
      <input type="text" name="location"><br>
      <label>Notes:</label><br>
      <textarea name="notes"></textarea><br>
      <input type="submit" value="Book">
    </form>
    </body>
    </html>
    <?php
}
?>
