#include <SPI.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL343.h>
#include <ICM42688.h>

// Define Chip Select pins for two ADXL343 sensors
#define ICM_CS0 10      // Chip Select for the IMU
#define ICM_CS1 0      // Chip Select for the IMU
#define ICM_CS2 16      // Chip Select for the IMU
#define ICM_CS3 14      // Chip Select for the IMU
#define ICM_CS4 41      // Chip Select for the IMU
#define ICM_CS5 31      // Chip Select for the IMU


// Initialize three objects for each sensor
ICM42688 imu0(SPI, ICM_CS0);
ICM42688 imu1(SPI1, ICM_CS1);
ICM42688 imu2(SPI, ICM_CS2);
ICM42688 imu3(SPI1, ICM_CS3);
ICM42688 imu4(SPI, ICM_CS4);
ICM42688 imu5(SPI1, ICM_CS5);

// Transmission delay
unsigned int transmissionDelay = 400;  // Default delay for transmission in microseconds

// Sensor enable flags
bool enableIMU0 = true;
bool enableIMU1 = true;
bool enableIMU2 = true;
bool enableIMU3 = true;
bool enableIMU4 = true;
bool enableIMU5 = true;

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
    SPI1.begin();


    if (enableIMU0) {
        Serial.println("Initializing IMU0...");
        int status0 = imu0.begin();
        int count = 0;
        while (status0 < 0 && count < 20) {
            Serial.print("Retrying IMU0 initialization. Attempt ");
            Serial.println(count + 1);
            status0 = imu0.begin();
            count++;
            delay(100); // Add a small delay between retries
        }
        if (status0 < 0) {
            Serial.println("Failed to initialize IMU0! Disabling.");
            enableIMU0 = false;
        } else {
            Serial.println("IMU0 initialized successfully.");
            imu0.setAccelODR(ICM42688::odr4k);
        }
    }

    if (enableIMU1) {
        Serial.println("Initializing IMU1...");
        int status1 = imu1.begin();
        int count = 0;
        while (status1 < 0 && count < 20) {
            Serial.print("Retrying IMU1 initialization. Attempt ");
            Serial.println(count + 1);
            status1 = imu1.begin();
            count++;
            delay(100); // Add a small delay between retries
        }
        if (status1 < 0) {
            Serial.println("Failed to initialize IMU1! Disabling.");
            enableIMU1 = false;
        } else {
            Serial.println("IMU1 initialized successfully.");
            imu1.setAccelODR(ICM42688::odr4k);
        }
    }

    if (enableIMU2) {
        Serial.println("Initializing IMU2...");
        int status2 = imu2.begin();
        int count = 0;
        while (status2 < 0 && count < 20) {
            Serial.print("Retrying IMU2 initialization. Attempt ");
            Serial.println(count + 1);
            status2 = imu2.begin();
            count++;
            delay(100); // Add a small delay between retries
        }
        if (status2 < 0) {
            Serial.println("Failed to initialize IMU2! Disabling.");
            enableIMU2 = false;
        } else {
            Serial.println("IMU2 initialized successfully.");
            imu2.setAccelODR(ICM42688::odr4k);
        }
    }

    if (enableIMU3) {
        Serial.println("Initializing IMU3...");
        int status3 = imu3.begin();
        int count = 0;
        while (status3 < 0 && count < 20) {
            Serial.print("Retrying IMU3 initialization. Attempt ");
            Serial.println(count + 1);
            status3 = imu3.begin();
            count++;
            delay(100); // Add a small delay between retries
        }
        if (status3 < 0) {
            Serial.println("Failed to initialize IMU3! Disabling.");
            enableIMU3 = false;
        } else {
            Serial.println("IMU3 initialized successfully.");
            imu3.setAccelODR(ICM42688::odr4k);
        }
    }

    if (enableIMU4) {
        Serial.println("Initializing IMU4...");
        int status4 = imu4.begin();
        int count = 0;
        while (status4 < 0 && count < 20) {
            Serial.print("Retrying IMU4 initialization. Attempt ");
            Serial.println(count + 1);
            status4 = imu4.begin();
            count++;
            delay(100); // Add a small delay between retries
        }
        if (status4 < 0) {
            Serial.println("Failed to initialize IMU4! Disabling.");
            enableIMU4 = false;
        } else {
            Serial.println("IMU4 initialized successfully.");
            imu4.setAccelODR(ICM42688::odr4k);
        }
    }

    if (enableIMU5) {
        Serial.println("Initializing IMU5...");
        int status5 = imu5.begin();
        int count = 0;
        while (status5 < 0 && count < 20) {
            Serial.print("Retrying IMU5 initialization. Attempt ");
            Serial.println(count + 1);
            status5 = imu5.begin();
            count++;
            delay(100); // Add a small delay between retries
        }
        if (status5 < 0) {
            Serial.println("Failed to initialize IMU5! Disabling.");
            enableIMU5 = false;
        } else {
            Serial.println("IMU5 initialized successfully.");
            imu5.setAccelODR(ICM42688::odr4k);
        }
    }

    Serial.println("Setup complete. Ready to read accelerometer data.");
}

char output[400];
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

    if (enableIMU0) {
        imu0.getAGT();
        offset += sprintf(output + offset, "0 %.1lu %.12f %.12f %.12f\n",
                          micros(), imu0.accX(), imu0.accY(), imu0.accZ());
    }

    if (enableIMU1) {
        imu1.getAGT();
        offset += sprintf(output + offset, "1 %.1lu %.12f %.12f %.12f\n",
                          micros(), imu1.accX(), imu1.accY(), imu1.accZ());
    }
    
    if (enableIMU2) {
        imu2.getAGT();
        offset += sprintf(output + offset, "2 %.1lu %.12f %.12f %.12f\n",
                          micros(), imu2.accX(), imu2.accY(), imu2.accZ());
    }
    
    if (enableIMU3) {
        imu3.getAGT();
        offset += sprintf(output + offset, "3 %.1lu %.12f %.12f %.12f\n",
                          micros(), imu3.accX(), imu3.accY(), imu3.accZ());
    }
    
    if (enableIMU4) {
        imu4.getAGT();
        offset += sprintf(output + offset, "4 %.1lu %.12f %.12f %.12f\n",
                          micros(), imu4.accX(), imu4.accY(), imu4.accZ());
    }
    
    if (enableIMU5) {
        imu5.getAGT();
        offset += sprintf(output + offset, "5 %.1lu %.12f %.12f %.12f\n",
                          micros(), imu5.accX(), imu5.accY(), imu5.accZ());
    }

    if (Serial.availableForWrite() > 100 * 8) {
        Serial.print(output);
    }

    delayMicroseconds(transmissionDelay);
}
