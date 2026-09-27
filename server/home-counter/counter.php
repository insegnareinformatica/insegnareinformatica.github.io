<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('Vary: Origin');
header('X-Content-Type-Options: nosniff');

$allowedOrigins = [
    'https://informaticainclasse.it',
    'https://insegnareinformatica.github.io',
];
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$method = $_SERVER['REQUEST_METHOD'] ?? '';

function failCounter(int $status): void {
    http_response_code($status);
    echo json_encode(['error' => 'Counter unavailable']);
    exit;
}

if (!in_array($origin, $allowedOrigins, true)) {
    failCounter(403);
}
header('Access-Control-Allow-Origin: ' . $origin);

if ($method === 'OPTIONS') {
    header('Access-Control-Allow-Methods: GET, OPTIONS');
    http_response_code(204);
    exit;
}
if ($method !== 'GET') {
    header('Allow: GET, OPTIONS');
    failCounter(405);
}

// c+ crea il file senza azzerarlo; tutte le operazioni avvengono sotto lo stesso lock.
$fp = @fopen(__DIR__ . '/counter.txt', 'c+');
if ($fp === false) {
    failCounter(500);
}
if (!flock($fp, LOCK_EX)) {
    fclose($fp);
    failCounter(500);
}

$contents = stream_get_contents($fp);
$text = $contents === false ? null : trim($contents);
$count = $text === '' ? 0 : filter_var($text, FILTER_VALIDATE_INT, [
    'options' => ['min_range' => 0, 'max_range' => 9007199254740990],
]);
if ($contents === false || $count === false) {
    flock($fp, LOCK_UN);
    fclose($fp);
    failCounter(500);
}

$value = (string) ($count + 1);
$written = rewind($fp) && fwrite($fp, $value) === strlen($value);
$saved = $written && ftruncate($fp, strlen($value)) && fflush($fp);
flock($fp, LOCK_UN);
fclose($fp);
if (!$saved) {
    failCounter(500);
}

echo json_encode(['value' => (int) $value]);
