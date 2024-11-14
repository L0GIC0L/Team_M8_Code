#include <SPI.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL343.h>
#include <ICM42688.h>

// Define Chip Select pins for two ADXL343 sensors
#define CS_SENSOR1 10  // Chip Select for first sensor
#define CS_SENSOR2 16  // Chip Select for second sensor
#define ICM_CS 17      // Chip Select for the IMU

// Initialize two ADXL343 objects for each sensor
Adafruit_ADXL343 adxl1 = Adafruit_ADXL343(CS_SENSOR1, &SPI, 12345);
Adafruit_ADXL343 adxl2 = Adafruit_ADXL343(CS_SENSOR2, &SPI, 12345);
ICM42688 imu(SPI, ICM_CS);

// Transmission delay
unsigned int transmissionDelay = 400;  // Default delay for transmission in microseconds

// Sensor enable flags
bool enableSensor1 = true;
bool enableSensor2 = true;
bool enableIMU = true;

void setup() {
    Serial.begin(460800);
    while (!Serial) {}  // Wait for Serial to initialize
    Serial.println("System online...");

    /*
    Serial.println("Enter transmission speed delay in microseconds (default: 400): ");
    while (!Serial.available()) {}
    transmissionDelay = Serial.parseInt();
    if (transmissionDelay <= 0) transmissionDelay = 400;
    Serial.print("Transmission speed set to: ");
    Serial.println(transmissionDelay);
    */

    Serial.println("Initializing SPI...");
    SPI.begin();

    // Initialize sensors based on user selection
    if (enableSensor1) {
        Serial.println("Initializing ADXL1");
        if (!adxl1.begin()) {
            Serial.println("Failed to initialize ADXL1 (CS 10)! Check wiring.");
            while (1);
        }
        Serial.println("ADXL1 initialized successfully.");
        delay(100);
        adxl1.setRange(ADXL343_RANGE_2_G);
    }

    if (enableSensor2) {
        Serial.println("Initializing ADXL2");
        if (!adxl2.begin()) {
            Serial.println("Failed to initialize ADXL2 (CS 36)! Check wiring.");
            while (1);
        }
        Serial.println("ADXL2 initialized successfully.");
        delay(100);
        adxl2.setRange(ADXL343_RANGE_2_G);
    }

    if (enableIMU) {
        Serial.println("Initializing IMU");
        if (!imu.begin()) {
            Serial.println("Failed to initialize IMU (CS 37)! Check wiring.");
            while (1);
        }
        Serial.println("IMU1 initialized successfully.");
        delay(100);
        imu.setAccelODR(ICM42688::odr4k);  // Set high data rate for the IMU
    }

    Serial.println("Setup complete. Reading accelerometer data...");
}

char output[200];
float gravity = 9.81;

void loop() {
    // Check for transmission delay update
    if (Serial.available() > 0) {
        int newDelay = Serial.parseInt();
        if (newDelay > 0) {
            transmissionDelay = newDelay;
            Serial.print("Transmission delay updated to: ");
            Serial.println(transmissionDelay);
        }
    }

    int offset = 0;

    if (enableSensor1) {
        sensors_event_t event1;
        adxl1.getEvent(&event1);
        offset += sprintf(output + offset, "1 %.1lu %.12f %.12f %.12f\n",
                          micros(), (event1.acceleration.x)/gravity, (event1.acceleration.y)/gravity, (event1.acceleration.z)/gravity);
    }

    if (enableSensor2) {
        sensors_event_t event2;
        adxl2.getEvent(&event2);
        offset += sprintf(output + offset, "2 %.1lu %.12f %.12f %.12f\n",
                          micros(), (event2.acceleration.x)/gravity, (event2.acceleration.y)/gravity, (event2.acceleration.z)/gravity);
    }

    if (enableIMU) {
        imu.getAGT();
        offset += sprintf(output + offset, "3 %.1lu %.12f %.12f %.12f\n",
                          micros(), imu.accX(), imu.accY(), imu.accZ());
    }

    if (Serial.availableForWrite() > 100 * 8) {
        Serial.print(output);
    }

    delayMicroseconds(transmissionDelay);
}
