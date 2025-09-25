<?php
try {
    $db = new PDO("sqlite:bookings.db");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $db->query("SELECT id, name, email, service, location, notes, datetime, duration, created_at FROM bookings ORDER BY datetime ASC");
    $bookings = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (Exception $e) {
    die("Error: " . $e->getMessage());
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>All Bookings</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; }
    h1 { color: #333; }
    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    th { background: #eee; }
    tr:nth-child(even) { background: #f9f9f9; }
  </style>
</head>
<body>
  <h1>All Bookings</h1>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Date/Time</th>
        <th>Duration (min)</th>
        <th>Name</th>
        <th>Email</th>
        <th>Service</th>
        <th>Location</th>
        <th>Notes</th>
        <th>Created At</th>
      </tr>
    </thead>
    <tbody>
      <?php foreach ($bookings as $b): ?>
        <tr>
          <td><?= htmlspecialchars($b['id']) ?></td>
          <td><?= htmlspecialchars($b['datetime']) ?></td>
          <td><?= htmlspecialchars($b['duration']) ?></td>
          <td><?= htmlspecialchars($b['name']) ?></td>
          <td><?= htmlspecialchars($b['email']) ?></td>
          <td><?= htmlspecialchars($b['service']) ?></td>
          <td><?= htmlspecialchars($b['location']) ?></td>
          <td><?= htmlspecialchars($b['notes']) ?></td>
          <td><?= htmlspecialchars($b['created_at']) ?></td>
        </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</body>
</html>