<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

// --- Configuration ---
// It's good practice to define limits like this at the top
define('BOOKINGS_PER_DAY_LIMIT', 4);

try {
    $db = new PDO("sqlite:bookings.db");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // --- Get Query Parameters ---
    // Get start/end dates from the URL, or use defaults (today to 30 days from now)
    $startDate = $_GET['start'] ?? date('Y-m-d');
    $endDate = $_GET['end'] ?? date('Y-m-d', strtotime('+30 days'));

    // --- Use a Prepared Statement for Security and Flexibility ---
    // This is the best practice even for SELECT statements with user input.
    $sql = "SELECT datetime FROM bookings 
            WHERE date(datetime) BETWEEN :start_date AND :end_date
            AND status != 'cancelled'";
            
    $stmt = $db->prepare($sql);
    $stmt->execute([
        ':start_date' => $startDate,
        ':end_date' => $endDate
    ]);

    // Fetch all results into an array of individual datetime strings
    $booked_slots = $stmt->fetchAll(PDO::FETCH_COLUMN, 0);

    // --- Calculate Fully Booked Dates (same logic as the Flask app) ---
    $date_counts = [];
    foreach ($booked_slots as $slot) {
        // Extract just the 'YYYY-MM-DD' part of the datetime string
        $date = substr($slot, 0, 10);
        // Count how many bookings occur on each date
        if (!isset($date_counts[$date])) {
            $date_counts[$date] = 0;
        }
        $date_counts[$date]++;
    }

    $fully_booked_dates = [];
    foreach ($date_counts as $date => $count) {
        if ($count >= BOOKINGS_PER_DAY_LIMIT) {
            $fully_booked_dates[] = $date;
        }
    }
    
    // --- Send the Final JSON Response ---
    // The structure now matches your Flask API's output
    echo json_encode([
        'booked_slots' => $booked_slots,
        'fully_booked_dates' => $fully_booked_dates
    ]);

} catch (Exception $e) {
    http_response_code(500); // Set a server error status code
    echo json_encode([
        "status" => "error",
        "message" => "An error occurred while fetching availability."
    ]);
    // For your own debugging, you would log the real error
    // error_log($e->getMessage());
}
