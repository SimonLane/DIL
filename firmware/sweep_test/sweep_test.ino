#include <SPI.h>

//galvos
const byte CS    = 12; 
const byte CLOCK = 13;
const byte DATA  = 11;



void setup() {
  Serial.begin(115200);
  while(!Serial){}
  SPI.begin();
  pinMode(CS, OUTPUT);
  digitalWrite(CS, HIGH);

  
}

void loop() {
  for(int i=0;i<1024;i++){set_galvo(i);delayMicroseconds(10);}
  for(int i=1023;i>-1;i--){set_galvo(i);delayMicroseconds(5);}
//  set_galvo(0);delay(4000);
//
//  set_galvo(1023);delay(4000);

}



void set_galvo(uint16_t value){
//  Serial.println(value);
  SPI.beginTransaction(SPISettings(14000000, MSBFIRST, SPI_MODE0));
  digitalWriteFast(CS, LOW);
  SPI.transfer(highByte(value << 2));
  SPI.transfer(lowByte(value));
  digitalWriteFast(CS, HIGH);
  SPI.endTransaction();
}
