unsigned long timestamp = 0;
float scale = 10;
float freqx = 1.0 / 1000;
float freqy = 1.0 / 100;
float freqz = 1.0 / 10;
char output[100];

float ax = 0.0;
float ay = 0.0;
float az = 0.0;

unsigned int transmissionDelay = 400;  // Default delay for transmission in microseconds

void setup() {
    // Initialize Serial communication
    Serial.begin(460800);  // Fast serial communication
    Serial.println("System online...");
    while (!Serial) {}  // Wait for serial to initialize

    // Prompt the user to input the transmission delay
    Serial.println("Enter transmission speed delay in microseconds (default: 400): ");
}

void loop() {  
    // Check if there's incoming data for new transmission delay or commands
    if (Serial.available() > 0) {
        int newDelay = Serial.parseInt();  // Read input as integer
        if (newDelay > 0) {
            transmissionDelay = newDelay;
            Serial.print("Transmission delay updated to: ");
            Serial.println(transmissionDelay);
        }
    }

    // Generate synthetic accelerometer data
    timestamp = micros();  // Capture timestamp
    ax = scale * sin(2 * PI * timestamp * freqx);
    ay = scale * sin(2 * PI * timestamp * freqy);
    az = scale * sin(2 * PI * timestamp * freqz);

    // Format output to reduce serial transmission load
    sprintf(output, "1 %lu %.6f %.6f %.6f\n", timestamp, ax, ay, az);

    // Send data if there is room in the buffer
    if (Serial.availableForWrite() > 100 * 8) {
        Serial.print(output);
    }

    // Add the transmission delay
    delayMicroseconds(transmissionDelay);
}
