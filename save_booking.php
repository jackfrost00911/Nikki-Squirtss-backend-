<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");
error_reporting(0); // Turn off error reporting to the screen for a clean JSON response

// Use PHPMailer classes
use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

// Load PHPMailer and our configuration file
require __DIR__ . "/PHPMailer/src/Exception.php";
require __DIR__ . "/PHPMailer/src/PHPMailer.php";
require __DIR__ . "/PHPMailer/src/SMTP.php";
require 'config.php'; // <-- Include our secure credentials

/**
 * Function to send an email using PHPMailer with credentials from config.
 * Moved outside the main try/catch block for better organization.
 * * @return bool True on success, false on failure.
 */
function sendEmail($to, $subject, $body) {
    $mail = new PHPMailer(true);
    try {
        $mail->isSMTP();
        $mail->Host = "smtp.gmail.com";
        $mail->SMTPAuth = true;
        $mail->Username = GMAIL_USER; // From config.php
        $mail->Password = GMAIL_PASS; // From config.php
        $mail->SMTPSecure = "tls";
        $mail->Port = 587;
        
        // --- Improvement: Set character set for emojis and special characters ---
        $mail->CharSet = 'UTF-8';

        $mail->setFrom(GMAIL_USER, FROM_NAME); // From config.php
        $mail->addAddress($to);

        $mail->isHTML(true);
        $mail->Subject = $subject;
        $mail->Body    = $body;

        $mail->send();
        return true; // Email sent successfully
    } catch (Exception $e) {
        // Log the detailed error for debugging, but don't show it to the user
        error_log("PHPMailer Error: " . $mail->ErrorInfo);
        return false; // Email failed to send
    }
}


try {
    // --- Database Connection ---
    $db = new PDO("sqlite:bookings.db");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $data = json_decode(file_get_contents("php://input"), true);

    // --- Improvement: Input Validation ---
    if (!$data) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Invalid JSON input."]);
        exit();
    }
    $requiredFields = ["name", "email", "service", "datetime"];
    $missingFields = [];
    foreach ($requiredFields as $field) {
        if (empty($data[$field])) {
            $missingFields[] = $field;
        }
    }
    if (!empty($missingFields)) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Missing required fields: " . implode(", ", $missingFields)]);
        exit();
    }

    // --- Save booking into database ---
    $stmt = $db->prepare("INSERT INTO bookings (name, email, service, location, notes, datetime) 
                          VALUES (:name, :email, :service, :location, :notes, :datetime)");
    $stmt->execute([
        ":name"     => $data["name"],
        ":email"    => $data["email"],
        ":service"  => $data["service"],
        ":location" => $data["location"] ?? "",
        ":notes"    => $data["notes"] ?? "",
        ":datetime" => $data["datetime"]
    ]);

    // --- Send Emails ---
    // --- Improvement: Sanitize all user data before putting it in an email ---
    $name     = htmlspecialchars($data['name']);
    $email    = htmlspecialchars($data['email']);
    $service  = htmlspecialchars($data['service']);
    $datetime = htmlspecialchars($data['datetime']);
    $location = htmlspecialchars($data['location'] ?? 'N/A');
    $notes    = htmlspecialchars($data['notes'] ?? 'N/A');

    // 1. Send alert to YOU
    $alertBody = "You have a new booking:<br><br>
                  <b>Name:</b> {$name}<br>
                  <b>Email:</b> {$email}<br>
                  <b>Service:</b> {$service}<br>
                  <b>Date:</b> {$datetime}<br>
                  <b>Location:</b> {$location}<br>
                  <b>Notes:</b> {$notes}";
    $adminEmailSent = sendEmail(ALERT_EMAIL, "🗓️ New Booking Alert", $alertBody);

    // 2. Send confirmation to CLIENT
    $clientEmailSent = false;
    if (!empty($data['email'])) {
        $clientBody = "Hi {$name},<br><br>
                       Thank you for booking! Here are your details:<br><br>
                       <b>Service:</b> {$service}<br>
                       <b>Date:</b> {$datetime}<br>
                       <b>Location:</b> {$location}<br><br>
                       We’ll be in touch soon.<br><br>
                       – Nikki’s Booking Desk";
        $clientEmailSent = sendEmail($data['email'], "✅ Your Booking Confirmation", $clientBody);
    }
    
    $emailStatus = ($adminEmailSent && $clientEmailSent) ? "All emails sent." : "Error sending one or more emails.";

    http_response_code(201);
    echo json_encode(["status" => "success", "message" => "Booking created.", "email_status" => $emailStatus]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["status" => "error", "message" => "A database error occurred."]);
    error_log("Database Error: " . $e->getMessage()); // Log the real error for yourself
}
