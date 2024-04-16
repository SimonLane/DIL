//doesnt work
#include "USBHost_t36.h"
#define USBBAUD 115200
uint32_t baud = USBBAUD;
uint32_t format = USBHOST_SERIAL_8N1;


USBHost myusb;
//USBHub hub1(myusb);
USBSerial userial(myusb);

void setup() {
  Serial.begin(115200);
  while (!Serial) {}

  
  myusb.begin();    // Start USBHost_t36 and USB devices.
  
  
  Serial.println("done!");

  
}

void loop() {
  myusb.Task();
  
  userial.begin(baud, format);
  userial.println("MRx100");
  userial.end();
  delay(1000);

}
