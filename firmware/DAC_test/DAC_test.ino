
const byte CS    = 12; 
const byte CLOCK = 13;
const byte DATA  = 11;

const byte Xo  = 31;
const byte Yo  = 29;
const byte Zo  = 27;

const byte Xi  = 32;
const byte Yi  = 30;
const byte Zi  = 28;

bool x_stage_flag = false; //flags for tracking when stage moves are complete
bool y_stage_flag = false;
bool z_stage_flag = false;

bool verbose = false;

const byte HALF_CLOCK_PERIOD = 2; //2 uS of clock period 

void setup() {
  Serial.begin(115200);
  pinMode(DATA, OUTPUT);
  pinMode(CLOCK, OUTPUT);
  pinMode(CS, OUTPUT);
  digitalWrite(CS, HIGH);
  digitalWrite(DATA, LOW);
  digitalWrite(CLOCK, LOW);
  pinMode(Xo, OUTPUT);
  pinMode(Yo, OUTPUT);
  pinMode(Zo, OUTPUT);
  pinMode(Xi, INPUT_PULLUP);
  pinMode(Yi, INPUT_PULLUP);
  pinMode(Zi, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(Xi), x_move_complete, FALLING);
  attachInterrupt(digitalPinToInterrupt(Yi), y_move_complete, FALLING);
  attachInterrupt(digitalPinToInterrupt(Zi), z_move_complete, FALLING);
  
}

void x_move_complete(){x_stage_flag = true;}
void y_move_complete(){y_stage_flag = true;}
void z_move_complete(){z_stage_flag = true;}

long unsigned int prev_report = 0;
long unsigned int prev_move = 0;

void report_status(int timer){
  if(micros() > prev_report + timer){
    prev_report = micros();
    Serial.println(z_stage_flag);
  }
}



void loop() {
checkSerial();
}

//~~~~~~~~~~~~~~~~~~~~~~~~~~ Serial communications ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
String device = "";
String command1 = "";
String command2 = "";
String command3 = "";
String command4 = "";
String command5 = "";

int serial_part = 0;
bool Verbose = true;

void checkSerial(){
  char rc;
  while (Serial.available()) {
   rc = Serial.read();
   if (rc == 47)      {serial_part = 1; device = "";command1 = "";command2 = "";}  // '/' char
   else if (rc == 46)      {serial_part += 1;}                                     // '.' char
   else if (rc == 59)      {respond(device,command1,command2,command3,command4,command5); serial_part = 0;}   // ';' char
   else if (serial_part == 1){device   += rc;}
   else if (serial_part == 2){command1 += rc;}
   else if (serial_part == 3){command2 += rc;}
   else if (serial_part == 4){command3 += rc;}
   else if (serial_part == 5){command4 += rc;}
   else if (serial_part == 6){command5 += rc;}
 }
}

void hablar(String parabla){
  if(Verbose == true){Serial.println(parabla);}
}

void respond(String device,String command1, String command2, String command3, String command4, String command5) {
    if(device == "hello")                         {Serial.println("Dual Illumination Lightsheet");}
// Scan command
    if(device == "G")                   {set_galvo(command1.toInt());} //Galvo command
    if(device == "X")                   {increment_stage(0);} //Stage command
    if(device == "Y")                   {increment_stage(1);} //Stage command
    if(device == "Z")                   {increment_stage(2);} //Stage command
    if(device == "S")                   {sweep(command1.toInt());}// Sweep galvos - transit time in millieconds
}


void sweep(uint32_t transit_time){
  //calculate step time
  Serial.print("sweeping...");
  Serial.println(millis());
  uint32_t s_t = round(transit_time*1000 / 1024.0); //10-bit DAC
  uint32_t prev_micros = 0;
  for(int i =0;i<1024;i++){
    while(micros() < prev_micros + s_t){} //delay for step time
    prev_micros = micros();
    set_galvo(i);
  }
  Serial.print("finished...");
  Serial.println(millis());
}


void move_z(int timer){
  if(millis() > prev_move + timer){
    prev_move = millis();
    increment_stage(2);
  }
}

void increment_stage(int axis){
  if(axis==2){
    z_stage_flag = false;
    digitalWrite(Zo,0);
    delayMicroseconds(1);
    digitalWrite(Zo,1);
  }
  if(axis==1){
    y_stage_flag = false;
    digitalWrite(Yo,0);
    delayMicroseconds(1);
    digitalWrite(Yo,1);
  }
  if(axis==0){
    x_stage_flag = false;
    digitalWrite(Xo,0);
    delayMicroseconds(1);
    digitalWrite(Xo,1);
  }
}

void set_galvo(uint16_t value){
  if(verbose){Serial.print(value);}
  digitalWrite(CS, LOW);//start of 12 bit data sequence
  digitalWrite(CLOCK, LOW);
  // Add 2 0's at the end of the data. A 10-bit data word should add 2 0 at the 
  // LSB bit (sub-LSB) since the DAC input latch is 12 bits wide.
  // (SEE TLC5615C DATASHEET)   
  value = value << 2;
  if(verbose){
    Serial.print("\t");
    Serial.println(value); }
  for (int i = 11; i >= 0; i--)//send the 12 bit sample data
  {
    digitalWrite(DATA, (value & (1 << i)) >> i);//DATA ready
    delayMicroseconds(HALF_CLOCK_PERIOD);
    digitalWrite(CLOCK, HIGH);//DAC get DATA at positive edge
    delayMicroseconds(HALF_CLOCK_PERIOD);
    digitalWrite(CLOCK, LOW);
  }
  digitalWrite(CS, HIGH);//end 12 bit data sequence
}
