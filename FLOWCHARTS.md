# 🏥 Qure Clinic Management System - Complete Flowcharts & Diagrams

**System Architecture & Data Flow Documentation**

---

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Authentication Flow](#authentication-flow)
3. [Complete Patient Journey](#complete-patient-journey)
4. [Appointment & Slot Management](#appointment--slot-management)
5. [Queue Management (Redis)](#queue-management-redis)
6. [Visit & Consultation Flow](#visit--consultation-flow)
7. [Prescription & Dispensing Flow](#prescription--dispensing-flow)
8. [Billing Flow (Auto & Manual)](#billing-flow-auto--manual)
9. [Inventory Management](#inventory-management)
10. [MongoDB Analytics & Logging](#mongodb-analytics--logging)
11. [Database Schema (ER Diagram)](#database-schema-er-diagram)

---

## System Architecture Overview

### Three-Tier Architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ Client Layer"]
        Web[Web Application]
        Mobile[Mobile App]
        Admin[Admin Dashboard]
    end

    subgraph API["⚡ FastAPI Application Layer"]
        Gateway[API Gateway]
        Auth[Authentication Middleware<br/>JWT Verification]

        subgraph Routes["API Routers"]
            R1[Auth Router]
            R2[Patient Router]
            R3[Appointment Router]
            R4[Visit Router]
            R5[Prescription Router]
            R6[Billing Router]
            R7[Inventory Router]
            R8[Queue Router]
            R9[Reports Router]
        end

        subgraph Services["Business Logic"]
            S1[Queue Service]
            S2[Billing Service]
            S3[Dispensing Service]
            S4[Mongo Service]
        end
    end

    subgraph Data["💾 Data Storage Layer"]
        PG[(PostgreSQL<br/>Primary Database)]
        Mongo[(MongoDB<br/>Analytics & Logs)]
        Redis[(Redis<br/>Queue & Cache)]
    end

    Web --> Gateway
    Mobile --> Gateway
    Admin --> Gateway

    Gateway --> Auth
    Auth --> Routes
    Routes --> Services

    Services --> PG
    Services --> Mongo
    Services --> Redis

    style Client fill:#e1f5ff
    style API fill:#f3e5f5
    style Data fill:#fff3e0
```

### Data Flow by Operation Type

```mermaid
flowchart LR
    subgraph Operations
        Read[Read Operations<br/>GET]
        Write[Write Operations<br/>POST/PATCH]
        Realtime[Real-time<br/>Queue]
    end

    subgraph Storage
        PG[(PostgreSQL)]
        Mongo[(MongoDB)]
        Redis[(Redis)]
    end

    Read -->|Query| PG
    PG -->|Return Data| Read

    Write -->|Insert/Update| PG
    Write -->|Audit Log| Mongo
    PG -->|Confirm| Write

    Realtime <-->|Pub/Sub| Redis

    style Operations fill:#e3f2fd
    style Storage fill:#fff3e0
```

---

## Authentication Flow

### Login & JWT Token Generation

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Auth as Auth Service
    participant DB as PostgreSQL

    Client->>API: POST /auth/login<br/>{username, password}
    API->>Auth: Validate credentials
    Auth->>DB: SELECT * FROM users<br/>WHERE username = ?
    DB-->>Auth: User record

    alt User Found
        Auth->>Auth: Verify password<br/>bcrypt.checkpw()

        alt Password Valid
            Auth->>Auth: Generate JWT<br/>jwt.encode(payload, SECRET_KEY)
            Auth->>Auth: Set expiration<br/>exp = now + 30 minutes
            Auth-->>API: {access_token, token_type, user_info}
            API-->>Client: 200 OK<br/>{access_token, user}

            Note over Client: Store token in localStorage

            Client->>API: GET /patients<br/>Header: Authorization: Bearer {token}
            API->>Auth: Verify JWT token
            Auth->>Auth: jwt.decode(token, SECRET_KEY)

            alt Token Valid
                Auth->>Auth: Extract user_id & role
                Auth-->>API: User context
                API->>API: Check RBAC permissions
                API->>DB: Query patients
                DB-->>API: Patient data
                API-->>Client: 200 OK + Data
            else Token Expired/Invalid
                Auth-->>API: Invalid token
                API-->>Client: 401 Unauthorized
            end

        else Password Invalid
            Auth-->>API: Invalid credentials
            API-->>Client: 401 Unauthorized
        end

    else User Not Found
        Auth-->>API: User not found
        API-->>Client: 401 Unauthorized
    end
```

### Role-Based Access Control (RBAC)

```mermaid
flowchart TD
    Request[Incoming Request] --> Token[Extract JWT Token]
    Token --> Verify[Verify Token Signature]

    Verify -->|Invalid| Reject[401 Unauthorized]
    Verify -->|Valid| Extract[Extract User Role]

    Extract --> CheckRole{User Role?}

    CheckRole -->|ADMIN| AdminAccess[Full Access<br/>All Endpoints]
    CheckRole -->|DOCTOR| DoctorAccess[Patients, Visits<br/>Prescriptions, Queue]
    CheckRole -->|PHARMACIST| PharmacistAccess[Inventory, Dispensing<br/>Prescriptions Read]
    CheckRole -->|RECEPTION| ReceptionAccess[Patients, Appointments<br/>Queue, Billing]

    AdminAccess --> Allow[✅ Allow Request]
    DoctorAccess --> CheckEndpoint{Endpoint Allowed?}
    PharmacistAccess --> CheckEndpoint
    ReceptionAccess --> CheckEndpoint

    CheckEndpoint -->|Yes| Allow
    CheckEndpoint -->|No| Deny[403 Forbidden]

    style Allow fill:#4caf50,color:#fff
    style Reject fill:#f44336,color:#fff
    style Deny fill:#ff9800,color:#fff
```

---

## Complete Patient Journey

### End-to-End Flow (Registration to Billing)

```mermaid
flowchart TD
    Start([🚪 Patient Arrives at Clinic]) --> CheckReg{Is Patient<br/>Registered?}

    CheckReg -->|No| RegPatient[📝 POST /patients<br/>Register New Patient<br/>- Name, DOB, Phone<br/>- Address, Emergency Contact<br/>- Allergies, Chronic Conditions]
    CheckReg -->|Yes| SearchPatient[🔍 GET /patients?search<br/>Search by Name/Phone/ID]

    RegPatient --> SavePatient[(💾 PostgreSQL<br/>INSERT INTO patients)]
    SearchPatient --> SavePatient

    SavePatient --> CheckAppt{Has<br/>Appointment?}

    CheckAppt -->|Yes| CheckInFlow[✅ POST /queue/checkin<br/>Check-in with Appointment ID<br/>- Verify slot<br/>- Generate token]
    CheckAppt -->|No| WalkInFlow[🚶 POST /queue/walk-in<br/>Add Walk-in Patient<br/>- Generate token<br/>- Add to queue]

    CheckInFlow --> QueueRedis[(🔴 Redis<br/>ZADD queue:date<br/>HSET token details)]
    WalkInFlow --> QueueRedis

    QueueRedis --> WaitQueue[⏳ GET /queue/today<br/>Display Queue Status<br/>Show token number]

    WaitQueue --> DoctorCall[🔔 POST /queue/next<br/>Doctor Calls Next Patient<br/>Update status: WITH_DOCTOR]

    DoctorCall --> StartVisit[🏥 POST /visits<br/>Start Consultation<br/>Link to patient & appointment]

    StartVisit --> SaveVisit[(💾 PostgreSQL<br/>INSERT INTO visits<br/>Status: IN_PROGRESS)]

    SaveVisit --> RecordVitals[📊 PATCH /visits/id<br/>Record Vitals<br/>- BP, Temp, Pulse<br/>- Weight, Height<br/>- SpO2]

    RecordVitals --> AddComplaints[📋 Add to visit:<br/>- Chief Complaints<br/>- Symptoms Duration]

    AddComplaints --> Examination[🔬 Doctor Examination<br/>POST /visits/id/notes<br/>- Clinical Observations<br/>- Physical Examination]

    Examination --> Diagnosis[🩺 PATCH /visits/id<br/>Add Diagnosis<br/>- Primary Diagnosis<br/>- Treatment Plan]

    Diagnosis --> NeedsMeds{Medicines<br/>Required?}

    NeedsMeds -->|Yes| CreatePrescription[💊 POST /prescriptions<br/>Create Prescription<br/>- Link to visit<br/>- Add medicines]
    NeedsMeds -->|No| CompleteVisitNoPx

    CreatePrescription --> AddMedicines[Add Prescription Items:<br/>For each medicine:<br/>- Medicine ID<br/>- Dosage, Frequency<br/>- Duration, Instructions]

    AddMedicines --> SavePrescription[(💾 PostgreSQL<br/>INSERT INTO prescriptions<br/>INSERT INTO prescription_items)]

    SavePrescription --> CompleteVisit[✅ POST /visits/id/complete<br/>Mark Visit as COMPLETED]

    CompleteVisitNoPx[✅ Complete Visit] --> CompleteVisit

    CompleteVisit --> SaveToMongo[(📊 MongoDB<br/>INSERT INTO visit_history<br/>Complete visit record)]

    SaveToMongo --> GenerateBill[💰 POST /billing<br/>Generate Invoice<br/>Mode: AUTO or MANUAL]

    GenerateBill --> BillingMode{Billing<br/>Mode?}

    BillingMode -->|AUTO| AutoBill[Auto-calculate from prescription<br/>- Fetch medicine prices<br/>- Calculate subtotal]
    BillingMode -->|MANUAL| ManualBill[Manual line items<br/>- Custom items<br/>- Consultation fee]

    AutoBill --> ApplyCharges[Apply charges:<br/>- Tax calculation<br/>- Apply discounts<br/>- Calculate total]
    ManualBill --> ApplyCharges

    ApplyCharges --> SaveInvoice[(💾 PostgreSQL<br/>INSERT INTO invoices<br/>Status: PENDING)]

    SaveInvoice --> ShowBill[📄 GET /billing/id<br/>Display Invoice to Patient]

    ShowBill --> ProcessPayment[💳 POST /billing/id/pay<br/>Process Payment<br/>Method: CASH/CARD/UPI]

    ProcessPayment --> UpdateInvoice[(💾 PostgreSQL<br/>UPDATE invoices<br/>Status: PAID<br/>paid_at: NOW)]

    UpdateInvoice --> LogPayment[(📊 MongoDB<br/>INSERT INTO audit_logs<br/>Action: PAYMENT_RECEIVED)]

    LogPayment --> HasPrescription{Has<br/>Prescription?}

    HasPrescription -->|Yes| Dispense[🏪 POST /dispensing<br/>Dispense Medicines<br/>Pharmacist role required]
    HasPrescription -->|No| EndFlow

    Dispense --> FetchStock[GET /inventory/medicines<br/>Check stock availability<br/>for each medicine]

    FetchStock --> CheckAvailability{All medicines<br/>in stock?}

    CheckAvailability -->|No| NotifyShortage[⚠️ Alert: Stock shortage<br/>Show alternatives]
    CheckAvailability -->|Yes| FIFOLogic

    NotifyShortage --> FIFOLogic[🔄 FIFO Logic<br/>Select batches:<br/>Earliest expiry first]

    FIFOLogic --> DeductStock[PATCH /inventory/batches/id<br/>Deduct stock from batches<br/>Update quantities]

    DeductStock --> UpdateBatch[(💾 PostgreSQL<br/>UPDATE medicine_batches<br/>SET quantity = quantity - dispensed)]

    UpdateBatch --> LogMovement[(📊 MongoDB<br/>INSERT INTO stock_movements<br/>Type: OUT)]

    LogMovement --> CheckLowStock{Stock below<br/>reorder level?}

    CheckLowStock -->|Yes| LowStockAlert[🚨 GET /inventory/low-stock<br/>Generate reorder alert]
    CheckLowStock -->|No| SaveDispensing

    LowStockAlert --> SaveDispensing[(💾 PostgreSQL<br/>INSERT INTO dispensing<br/>INSERT INTO dispensing_items)]

    SaveDispensing --> PrintReceipt[🖨️ Print Receipt & Prescription]

    PrintReceipt --> UpdateQueue[(🔴 Redis<br/>HSET token status: COMPLETED<br/>ZREM from active queue)]

    UpdateQueue --> EndFlow([✅ Patient Journey Complete])

    style Start fill:#4caf50,color:#fff
    style EndFlow fill:#2196f3,color:#fff
    style SavePatient fill:#ff9800
    style SaveVisit fill:#ff9800
    style SavePrescription fill:#ff9800
    style SaveInvoice fill:#ff9800
    style UpdateBatch fill:#ff9800
    style QueueRedis fill:#e91e63
    style UpdateQueue fill:#e91e63
    style SaveToMongo fill:#00bcd4
    style LogPayment fill:#00bcd4
    style LogMovement fill:#00bcd4
```

---

## Appointment & Slot Management

### Doctor Slot Creation & Patient Booking

```mermaid
flowchart TD
    subgraph Admin["👨‍⚕️ Doctor/Admin Actions"]
        CreateSlot[POST /slots/bulk<br/>Create Multiple Slots]
        BlockSlot[PATCH /slots/id/block<br/>Block slot for break/leave]
    end

    CreateSlot --> SlotDetails[Slot Details:<br/>- Doctor ID<br/>- Date<br/>- Start time, End time<br/>- Duration 15/30 mins]

    SlotDetails --> SaveSlots[(💾 PostgreSQL<br/>INSERT INTO slots<br/>Batch insert)]

    BlockSlot --> UpdateSlot[(💾 PostgreSQL<br/>UPDATE slots<br/>SET is_blocked = true)]

    SaveSlots --> Available[Slots Available]
    UpdateSlot --> Available

    subgraph Reception["📞 Reception Actions"]
        SearchSlots[GET /slots?doctor&date<br/>Find available slots]
        BookAppt[POST /appointments<br/>Book appointment]
    end

    Available --> SearchSlots

    SearchSlots --> ShowSlots[Display available slots<br/>Filter by:<br/>- Doctor<br/>- Date<br/>- Time range]

    ShowSlots --> PatientSelect[Patient selects slot]

    PatientSelect --> BookAppt

    BookAppt --> ValidateSlot{Slot still<br/>available?}

    ValidateSlot -->|No| SlotTaken[❌ Slot already booked<br/>Show alternatives]
    ValidateSlot -->|Yes| CreateAppt

    SlotTaken --> SearchSlots

    CreateAppt[Create appointment record] --> SaveAppt[(💾 PostgreSQL<br/>INSERT INTO appointments<br/>Status: SCHEDULED)]

    SaveAppt --> SendConfirmation[📧 Send confirmation<br/>SMS/Email/WhatsApp]

    SendConfirmation --> ApptBooked([✅ Appointment Booked])

    subgraph ApptDay["📅 On Appointment Day"]
        PatientArrives[Patient arrives]
        CheckIn[POST /queue/checkin]
    end

    ApptBooked -.-> PatientArrives
    PatientArrives --> CheckIn

    CheckIn --> ValidateAppt{Valid<br/>appointment?}

    ValidateAppt -->|No| WalkIn[Add as walk-in instead]
    ValidateAppt -->|Yes| UpdateApptStatus

    UpdateApptStatus[(💾 PostgreSQL<br/>UPDATE appointments<br/>Status: CHECKED_IN)] --> AddToQueue

    AddToQueue[(🔴 Redis<br/>Add to queue with priority<br/>Appointment > Walk-in)]

    WalkIn --> AddToQueue

    style SaveSlots fill:#ff9800
    style SaveAppt fill:#ff9800
    style UpdateApptStatus fill:#ff9800
    style AddToQueue fill:#e91e63
```

---

## Queue Management (Redis)

### Real-Time Queue Operations

```mermaid
flowchart TD
    subgraph Entry["🚪 Queue Entry Points"]
        CheckIn[POST /queue/checkin<br/>With appointment]
        WalkIn[POST /queue/walk-in<br/>Without appointment]
    end

    CheckIn --> GenerateToken[Generate Token<br/>Format: YYYYMMDD-NNN<br/>Example: 20260217-001]
    WalkIn --> GenerateToken

    GenerateToken --> RedisOps1{Redis Operations}

    RedisOps1 -->|1| IncrCounter[INCR queue:counter:date<br/>Get next token number]
    RedisOps1 -->|2| AddToSortedSet[ZADD queue:date<br/>score: timestamp<br/>member: token]
    RedisOps1 -->|3| SaveTokenData[HSET queue:token:date:num<br/>patient_id, name, type<br/>status: WAITING]

    IncrCounter --> Display
    AddToSortedSet --> Display
    SaveTokenData --> Display[🖥️ Display on Screen<br/>Token: 001<br/>Status: Waiting]

    Display --> Monitor[GET /queue/today<br/>Monitor queue status]

    Monitor --> ShowQueue[Show all tokens:<br/>- Currently serving<br/>- Waiting list<br/>- Completed<br/>- Skipped]

    ShowQueue --> DoctorReady[👨‍⚕️ Doctor ready for next]

    DoctorReady --> CallNext[POST /queue/next<br/>Call next patient]

    CallNext --> RedisOps2{Redis Operations}

    RedisOps2 -->|1| GetFirst[ZRANGE queue:date 0 0<br/>Get first token in queue]
    RedisOps2 -->|2| UpdateStatus1[HSET queue:token:date:num<br/>status: WITH_DOCTOR<br/>called_at: timestamp]
    RedisOps2 -->|3| SetCurrent[SET queue:current:date<br/>token_number]

    GetFirst --> NotifyPatient
    UpdateStatus1 --> NotifyPatient
    SetCurrent --> NotifyPatient[📢 Notify Patient<br/>Display: Token 001<br/>Doctor Room 3]

    NotifyPatient --> ConsultationStart[🩺 Consultation begins]

    ConsultationStart --> VisitComplete[Visit completed]

    VisitComplete --> UpdateComplete[PATCH /queue/token/status<br/>status: COMPLETED]

    UpdateComplete --> RedisOps3{Redis Operations}

    RedisOps3 -->|1| UpdateStatus2[HSET queue:token:date:num<br/>status: COMPLETED<br/>completed_at: timestamp]
    RedisOps3 -->|2| RemoveFromQueue[ZREM queue:date token<br/>Remove from active queue]

    UpdateStatus2 --> UpdateDisplay
    RemoveFromQueue --> UpdateDisplay[🖥️ Update Display<br/>Remove completed token]

    UpdateDisplay --> NextPatient[Ready for next patient]

    NextPatient --> DoctorReady

    subgraph Skip["⏭️ Skip Token Flow"]
        SkipPatient[Patient not present]
        SkipAction[PATCH /queue/token/status<br/>status: SKIPPED]
    end

    ShowQueue -.->|If patient absent| SkipPatient
    SkipPatient --> SkipAction
    SkipAction --> RemoveFromQueue

    subgraph EOD["🌙 End of Day"]
        DayEnd[End of day]
        GetStats[GET /queue/today/summary]
        SaveSummary[(📊 MongoDB<br/>Save daily summary)]
    end

    DayEnd --> GetStats
    GetStats --> SaveSummary

    style IncrCounter fill:#e91e63
    style AddToSortedSet fill:#e91e63
    style SaveTokenData fill:#e91e63
    style GetFirst fill:#e91e63
    style UpdateStatus1 fill:#e91e63
    style UpdateStatus2 fill:#e91e63
    style RemoveFromQueue fill:#e91e63
    style SetCurrent fill:#e91e63
    style SaveSummary fill:#00bcd4
```

### Redis Data Structure

```mermaid
flowchart LR
    subgraph Keys["🔴 Redis Keys"]
        K1[queue:2026-02-17<br/>Sorted Set]
        K2[queue:counter:2026-02-17<br/>Integer]
        K3[queue:token:2026-02-17:001<br/>Hash]
        K4[queue:current:2026-02-17<br/>String]
    end

    subgraph Values["📊 Data Values"]
        V1[Score: 1708156800<br/>Member: 001<br/>Score: 1708156815<br/>Member: 002]
        V2[Value: 5<br/>Last token issued]
        V3[patient_id: 123<br/>patient_name: John<br/>type: APPOINTMENT<br/>status: WITH_DOCTOR<br/>checked_in_at: timestamp<br/>called_at: timestamp]
        V4[Value: 001<br/>Currently serving]
    end

    K1 -.-> V1
    K2 -.-> V2
    K3 -.-> V3
    K4 -.-> V4
```

---

## Visit & Consultation Flow

### Complete Consultation Process

```mermaid
flowchart TD
    Start[Patient called to room] --> CreateVisit[POST /visits<br/>Create visit record]

    CreateVisit --> VisitData[Visit data:<br/>- Patient ID<br/>- Doctor ID<br/>- Appointment ID if exists]

    VisitData --> SaveVisit[(💾 PostgreSQL<br/>INSERT INTO visits<br/>Status: IN_PROGRESS)]

    SaveVisit --> RecordVitals[PATCH /visits/id<br/>Record vital signs]

    RecordVitals --> VitalsData[Vitals JSON:<br/>- Blood pressure: 120/80<br/>- Temperature: 98.6°F<br/>- Pulse: 72 bpm<br/>- Weight: 70 kg<br/>- Height: 170 cm<br/>- SpO2: 98%]

    VitalsData --> UpdateVitals[(💾 PostgreSQL<br/>UPDATE visits<br/>SET vitals = JSON)]

    UpdateVitals --> RecordComplaint[Record chief complaint]

    RecordComplaint --> ComplaintData[Chief complaint:<br/>- Fever since 3 days<br/>- Cough and cold<br/>- Body ache]

    ComplaintData --> UpdateComplaint[(💾 PostgreSQL<br/>UPDATE visits<br/>SET chief_complaint = text)]

    UpdateComplaint --> ClinicalNotes[POST /visits/id/notes<br/>Add clinical notes]

    ClinicalNotes --> NoteCategories{Note<br/>Category?}

    NoteCategories -->|SYMPTOM| SymptomNote[High fever<br/>Dry cough<br/>Fatigue]
    NoteCategories -->|OBSERVATION| ObservationNote[Throat inflammation<br/>Lung sounds clear<br/>No chest congestion]
    NoteCategories -->|DIAGNOSIS| DiagnosisNote[Viral upper respiratory<br/>tract infection]
    NoteCategories -->|TREATMENT| TreatmentNote[Rest for 3-4 days<br/>Stay hydrated<br/>Steam inhalation]

    SymptomNote --> SaveNotes
    ObservationNote --> SaveNotes
    DiagnosisNote --> SaveNotes
    TreatmentNote --> SaveNotes

    SaveNotes[(💾 PostgreSQL<br/>INSERT INTO clinical_notes)] --> AddDiagnosis

    AddDiagnosis[PATCH /visits/id<br/>Add diagnosis & treatment plan]

    AddDiagnosis --> DiagnosisDetails[Diagnosis: Viral URTI<br/>Treatment plan:<br/>- Medicines as prescribed<br/>- Follow-up if needed]

    DiagnosisDetails --> UpdateVisit[(💾 PostgreSQL<br/>UPDATE visits<br/>diagnosis, treatment_plan)]

    UpdateVisit --> NeedsPrescription{Prescription<br/>needed?}

    NeedsPrescription -->|Yes| CreatePx[POST /prescriptions]
    NeedsPrescription -->|No| CompleteVisit

    CreatePx --> CompleteVisit[POST /visits/id/complete]

    CompleteVisit --> FinalizeVisit[(💾 PostgreSQL<br/>UPDATE visits<br/>Status: COMPLETED<br/>completed_at: NOW)]

    FinalizeVisit --> SaveHistory[(📊 MongoDB<br/>INSERT INTO visit_history<br/>Complete visit snapshot)]

    SaveHistory --> LogAudit[(📊 MongoDB<br/>INSERT INTO audit_logs<br/>Action: VISIT_COMPLETED)]

    LogAudit --> End([✅ Visit Complete])

    style SaveVisit fill:#ff9800
    style UpdateVitals fill:#ff9800
    style UpdateComplaint fill:#ff9800
    style SaveNotes fill:#ff9800
    style UpdateVisit fill:#ff9800
    style FinalizeVisit fill:#ff9800
    style SaveHistory fill:#00bcd4
    style LogAudit fill:#00bcd4
```

---

## Prescription & Dispensing Flow

### From Prescription to Dispensing (FIFO Logic)

```mermaid
flowchart TD
    Doctor[👨‍⚕️ Doctor prescribes] --> CreatePx[POST /prescriptions<br/>Create prescription]

    CreatePx --> PxDetails[Prescription details:<br/>- Visit ID<br/>- Patient ID<br/>- Doctor ID]

    PxDetails --> SavePx[(💾 PostgreSQL<br/>INSERT INTO prescriptions)]

    SavePx --> AddItems[Add prescription items]

    AddItems --> ForEachMed[For each medicine:]

    ForEachMed --> ItemDetails[Item details:<br/>- Medicine ID<br/>- Dosage: 500mg<br/>- Frequency: Twice daily<br/>- Duration: 5 days<br/>- Instructions: After meals]

    ItemDetails --> SaveItems[(💾 PostgreSQL<br/>INSERT INTO prescription_items)]

    SaveItems --> MoreMeds{More<br/>medicines?}

    MoreMeds -->|Yes| ForEachMed
    MoreMeds -->|No| PxComplete

    PxComplete[Prescription complete] --> ViewPx[GET /prescriptions/id]

    ViewPx --> PrintPx[GET /prescriptions/id/print<br/>Generate printable format]

    PrintPx --> ToPharmacy[📄 Send to pharmacy]

    ToPharmacy --> Pharmacist[🧑‍⚕️ Pharmacist receives]

    Pharmacist --> ReviewPx[Review prescription<br/>Check for interactions]

    ReviewPx --> StartDispense[POST /dispensing<br/>Start dispensing process]

    StartDispense --> VerifyPayment{Payment<br/>confirmed?}

    VerifyPayment -->|No| RequestPayment[Request payment first]
    VerifyPayment -->|Yes| CheckStock

    RequestPayment --> VerifyPayment

    CheckStock[GET /inventory/medicines<br/>Check stock availability]

    CheckStock --> FetchBatches[For each medicine:<br/>Fetch available batches]

    FetchBatches --> QueryBatches[(💾 PostgreSQL<br/>SELECT * FROM medicine_batches<br/>WHERE medicine_id = ?<br/>AND quantity > 0<br/>AND expiry_date > CURRENT_DATE<br/>ORDER BY expiry_date ASC)]

    QueryBatches --> HasStock{Stock<br/>available?}

    HasStock -->|No| OutOfStock[❌ Out of stock<br/>Notify doctor<br/>Suggest alternatives]
    HasStock -->|Yes| FIFOLogic

    OutOfStock --> CheckAlternatives{Alternatives<br/>available?}
    CheckAlternatives -->|Yes| FIFOLogic
    CheckAlternatives -->|No| PartialDispense[Mark as partial dispensing]

    FIFOLogic[🔄 Apply FIFO Logic<br/>Select batch with:<br/>- Earliest expiry date<br/>- Sufficient quantity]

    FIFOLogic --> SelectBatch[Selected batch:<br/>Batch: ABC123<br/>Expiry: 2026-06-30<br/>Available: 100 units<br/>Required: 10 units]

    SelectBatch --> CalculateQty[Calculate quantity:<br/>Required = dosage × frequency × duration<br/>Example: 1 × 2 × 5 = 10 tablets]

    CalculateQty --> DeductStock[PATCH /inventory/batches/id<br/>Deduct stock]

    DeductStock --> UpdateBatch[(💾 PostgreSQL<br/>UPDATE medicine_batches<br/>SET quantity = quantity - 10<br/>WHERE id = batch_id)]

    UpdateBatch --> LogMovement[(📊 MongoDB<br/>INSERT INTO stock_movements<br/>Movement type: OUT<br/>Quantity: 10<br/>Batch: ABC123)]

    LogMovement --> CheckReorder{Stock < reorder<br/>level?}

    CheckReorder -->|Yes| CreateAlert[Generate low stock alert<br/>GET /inventory/low-stock]
    CheckReorder -->|No| RecordDispense

    CreateAlert --> NotifyAdmin[📧 Notify admin/purchaser]

    NotifyAdmin --> RecordDispense

    RecordDispense[Record dispensing]

    RecordDispense --> SaveDispense[(💾 PostgreSQL<br/>INSERT INTO dispensing<br/>dispensed_by: pharmacist_id<br/>dispensed_at: NOW)]

    SaveDispense --> SaveDispenseItems[(💾 PostgreSQL<br/>INSERT INTO dispensing_items<br/>For each medicine:<br/>- medicine_id<br/>- batch_id<br/>- quantity<br/>- unit_price)]

    SaveDispenseItems --> UpdatePxStatus[(💾 PostgreSQL<br/>UPDATE prescriptions<br/>SET dispensed = true)]

    UpdatePxStatus --> PrintLabel[🖨️ Print medicine labels<br/>Dosage instructions]

    PrintLabel --> PackMedicines[📦 Pack medicines<br/>Label bottles/strips]

    PackMedicines --> HandOver[Hand over to patient<br/>Explain dosage]

    HandOver --> Complete([✅ Dispensing Complete])

    style SavePx fill:#ff9800
    style SaveItems fill:#ff9800
    style QueryBatches fill:#ff9800
    style UpdateBatch fill:#ff9800
    style SaveDispense fill:#ff9800
    style SaveDispenseItems fill:#ff9800
    style UpdatePxStatus fill:#ff9800
    style LogMovement fill:#00bcd4
```

---

## Billing Flow (Auto & Manual)

### Invoice Generation with Two Modes

```mermaid
flowchart TD
    Start[Visit completed] --> InitBill[POST /billing<br/>Initiate billing]

    InitBill --> SelectMode{Billing<br/>Mode?}

    SelectMode -->|AUTO| AutoMode[AUTO MODE<br/>From prescription]
    SelectMode -->|MANUAL| ManualMode[MANUAL MODE<br/>Custom items]

    AutoMode --> FetchPx[Fetch prescription details]

    FetchPx --> QueryPx[(💾 PostgreSQL<br/>SELECT * FROM prescriptions<br/>JOIN prescription_items<br/>JOIN medicines)]

    QueryPx --> PxItems[Get all medicines:<br/>- Name<br/>- Quantity<br/>- Unit price]

    PxItems --> CalcMedTotal[Calculate medicine total:<br/>Sum item_price × quantity]

    ManualMode --> AddLineItems[Add custom line items:<br/>- Consultation fee<br/>- Procedure charges<br/>- Lab tests<br/>- Other charges]

    AddLineItems --> ManualTotal[Calculate manual total:<br/>Sum all line items]

    CalcMedTotal --> CalcSubtotal
    ManualTotal --> CalcSubtotal[Calculate subtotal]

    CalcSubtotal --> ApplyDiscount{Apply<br/>discount?}

    ApplyDiscount -->|Yes| DiscountCalc[Discount calculation:<br/>- Percentage: 10%<br/>- Fixed: $50<br/>New subtotal = subtotal - discount]
    ApplyDiscount -->|No| CalcTax

    DiscountCalc --> CalcTax[Calculate tax:<br/>Tax = subtotal × 0.18<br/>18% GST/VAT]

    CalcTax --> CalcTotal[Calculate total:<br/>Total = subtotal - discount + tax]

    CalcTotal --> CreateInvoice[Create invoice record]

    CreateInvoice --> InvoiceDetails[Invoice details:<br/>- Invoice number: INV-2026-001<br/>- Patient ID<br/>- Prescription ID if AUTO<br/>- Mode: AUTO/MANUAL<br/>- Subtotal<br/>- Discount<br/>- Tax<br/>- Total<br/>- Status: PENDING]

    InvoiceDetails --> SaveInvoice[(💾 PostgreSQL<br/>INSERT INTO invoices)]

    SaveInvoice --> SaveLineItems[(💾 PostgreSQL<br/>INSERT INTO invoice_items<br/>All line items)]

    SaveLineItems --> DisplayInvoice[GET /billing/id<br/>Display invoice to patient]

    DisplayInvoice --> WaitPayment[⏳ Status: PENDING<br/>Awaiting payment]

    WaitPayment --> ProcessPayment[POST /billing/id/pay<br/>Process payment]

    ProcessPayment --> SelectPaymentMethod{Payment<br/>Method?}

    SelectPaymentMethod -->|CASH| CashPayment[Cash payment<br/>Issue receipt]
    SelectPaymentMethod -->|CARD| CardPayment[Card payment<br/>Process via POS]
    SelectPaymentMethod -->|UPI| UPIPayment[UPI payment<br/>Scan QR code]

    CashPayment --> UpdateInvoice
    CardPayment --> UpdateInvoice
    UPIPayment --> UpdateInvoice

    UpdateInvoice[Update invoice status]

    UpdateInvoice --> SavePayment[(💾 PostgreSQL<br/>UPDATE invoices<br/>SET status = PAID<br/>payment_method = method<br/>paid_at = NOW)]

    SavePayment --> LogPayment[(📊 MongoDB<br/>INSERT INTO audit_logs<br/>Action: PAYMENT_RECEIVED)]

    LogPayment --> UpdateDailySummary[(📊 MongoDB<br/>UPDATE daily_summaries<br/>Increment total_revenue)]

    UpdateDailySummary --> PrintReceipt[🖨️ Print receipt]

    PrintReceipt --> Complete([✅ Billing Complete])

    style QueryPx fill:#ff9800
    style SaveInvoice fill:#ff9800
    style SaveLineItems fill:#ff9800
    style SavePayment fill:#ff9800
    style LogPayment fill:#00bcd4
    style UpdateDailySummary fill:#00bcd4
```

### Invoice Data Structure

```mermaid
flowchart TD
    Invoice[Invoice Record] --> Header[Header Information]
    Invoice --> Items[Line Items]
    Invoice --> Summary[Summary]

    Header --> H1[Invoice Number: INV-2026-001<br/>Date: 2026-02-17<br/>Patient: John Doe<br/>Doctor: Dr. Smith]

    Items --> I1[Item 1: Paracetamol 500mg<br/>Quantity: 10<br/>Price: $5.00]
    Items --> I2[Item 2: Amoxicillin 250mg<br/>Quantity: 15<br/>Price: $12.00]
    Items --> I3[Item 3: Consultation Fee<br/>Quantity: 1<br/>Price: $30.00]

    Summary --> S1[Subtotal: $47.00<br/>Discount: -$5.00<br/>Tax 18%: $7.56<br/>Total: $49.56<br/>Payment: CARD<br/>Status: PAID]
```

---

## Inventory Management

### Stock Management with Batch Tracking

```mermaid
flowchart TD
    Start([Inventory Operations]) --> Action{Action Type?}

    Action -->|Add Medicine| AddMedicine[POST /inventory/medicines<br/>Add new medicine to catalog]
    Action -->|Add Stock| AddStock[POST /inventory/batches<br/>Add new batch]
    Action -->|Check Stock| ViewStock[GET /inventory/medicines<br/>View stock levels]
    Action -->|Dispense| Dispense[Dispensing flow<br/>FIFO deduction]

    AddMedicine --> MedDetails[Medicine details:<br/>- Name<br/>- Generic name<br/>- Manufacturer<br/>- Unit price<br/>- Reorder level<br/>- Dosage form]

    MedDetails --> SaveMed[(💾 PostgreSQL<br/>INSERT INTO medicines)]

    AddStock --> BatchDetails[Batch details:<br/>- Medicine ID<br/>- Batch number<br/>- Quantity<br/>- Expiry date<br/>- Cost price<br/>- Supplier]

    BatchDetails --> ValidateExpiry{Expiry date<br/>valid?}

    ValidateExpiry -->|< 3 months| WarnExpiry[⚠️ Warning: Near expiry]
    ValidateExpiry -->|> 3 months| SaveBatch

    WarnExpiry --> ConfirmAdd{Still add?}
    ConfirmAdd -->|Yes| SaveBatch
    ConfirmAdd -->|No| Cancel([❌ Cancelled])

    SaveBatch[(💾 PostgreSQL<br/>INSERT INTO medicine_batches)]

    SaveBatch --> LogStockIn[(📊 MongoDB<br/>INSERT INTO stock_movements<br/>Type: IN<br/>Quantity: added)]

    ViewStock --> QueryStock[(💾 PostgreSQL<br/>SELECT m.*, <br/>SUM(mb.quantity) as total_stock<br/>FROM medicines m<br/>LEFT JOIN medicine_batches mb<br/>GROUP BY m.id)]

    QueryStock --> DisplayStock[Display medicines with:<br/>- Total stock<br/>- Available batches<br/>- Expiry dates<br/>- Status]

    DisplayStock --> CheckLowStock{Stock < reorder<br/>level?}

    CheckLowStock -->|Yes| LowStockList[GET /inventory/low-stock<br/>Show low stock items]
    CheckLowStock -->|No| StockOK

    LowStockList --> CreatePO[📝 Create purchase order<br/>External process]

    Dispense --> FIFOSelect[Select batch:<br/>ORDER BY expiry_date ASC<br/>LIMIT 1]

    FIFOSelect --> DeductQty[PATCH /inventory/batches/id<br/>Reduce quantity]

    DeductQty --> UpdateBatch[(💾 PostgreSQL<br/>UPDATE medicine_batches<br/>SET quantity = quantity - dispensed)]

    UpdateBatch --> LogStockOut[(📊 MongoDB<br/>INSERT INTO stock_movements<br/>Type: OUT)]

    LogStockOut --> CheckZero{Batch quantity<br/>= 0?}

    CheckZero -->|Yes| MarkEmpty[Mark batch as exhausted<br/>Keep for records]
    CheckZero -->|No| StockOK

    MarkEmpty --> StockOK([✅ Stock Updated])

    SaveMed --> StockOK
    LogStockIn --> StockOK

    style SaveMed fill:#ff9800
    style SaveBatch fill:#ff9800
    style QueryStock fill:#ff9800
    style UpdateBatch fill:#ff9800
    style LogStockIn fill:#00bcd4
    style LogStockOut fill:#00bcd4
```

### Expiry Tracking & Alerts

```mermaid
flowchart TD
    Scheduler[Daily Scheduled Job] --> CheckExpiry[Check expiring batches]

    CheckExpiry --> Query[(💾 PostgreSQL<br/>SELECT * FROM medicine_batches<br/>WHERE expiry_date BETWEEN<br/>CURRENT_DATE AND<br/>CURRENT_DATE + INTERVAL '90 days'<br/>AND quantity > 0)]

    Query --> Results{Any expiring<br/>batches?}

    Results -->|Yes| CategorizeExpiry[Categorize by urgency]
    Results -->|No| NoAction([No action needed])

    CategorizeExpiry --> Critical{Expiry in<br/>30 days?}

    Critical -->|Yes| CriticalAlert[🚨 CRITICAL Alert<br/>Send email + SMS<br/>High priority]
    Critical -->|No| WarningCheck

    WarningCheck{Expiry in<br/>60 days?}

    WarningCheck -->|Yes| WarningAlert[⚠️ WARNING Alert<br/>Send email<br/>Medium priority]
    WarningCheck -->|No| InfoAlert

    InfoAlert[ℹ️ INFO Alert<br/>Dashboard notification<br/>Low priority]

    CriticalAlert --> LogAlert
    WarningAlert --> LogAlert
    InfoAlert --> LogAlert

    LogAlert[(📊 MongoDB<br/>INSERT INTO audit_logs<br/>Alert type & details)]

    LogAlert --> Suggestions[Generate suggestions:<br/>- Return to supplier<br/>- Offer discount<br/>- Use for camps/donations]

    Suggestions --> End([Alert sent])

    style Query fill:#ff9800
    style LogAlert fill:#00bcd4
```

---

## MongoDB Analytics & Logging

### Complete Logging & Analytics System

```mermaid
flowchart TD
    subgraph Triggers["🎯 Event Triggers"]
        E1[User Action<br/>Create/Update/Delete]
        E2[Visit Completed]
        E3[Stock Movement]
        E4[End of Day]
    end

    subgraph Processing["⚙️ Processing"]
        P1[Extract event data]
        P2[Format for MongoDB]
        P3[Add metadata]
    end

    subgraph Collections["📊 MongoDB Collections"]
        C1[(audit_logs)]
        C2[(visit_history)]
        C3[(stock_movements)]
        C4[(daily_summaries)]
    end

    E1 --> P1
    E2 --> P1
    E3 --> P1
    E4 --> P1

    P1 --> P2
    P2 --> P3

    P3 --> Route{Event Type?}

    Route -->|User Action| C1
    Route -->|Visit| C2
    Route -->|Stock| C3
    Route -->|Daily Rollup| C4

    C1 --> AuditStructure[Document:<br/>timestamp: ISODate<br/>user: object<br/>action: string<br/>resource: object<br/>changes: object<br/>ip_address: string]

    C2 --> VisitStructure[Document:<br/>visit_id: int<br/>patient: object<br/>doctor: object<br/>vitals: object<br/>diagnosis: string<br/>prescription: array<br/>visit_date: ISODate]

    C3 --> StockStructure[Document:<br/>medicine: object<br/>batch_number: string<br/>movement_type: enum<br/>quantity: int<br/>reason: string<br/>performed_by: object<br/>timestamp: ISODate]

    C4 --> DailySummary[Document:<br/>date: ISODate<br/>total_patients: int<br/>total_visits: int<br/>total_revenue: decimal<br/>medicines_dispensed: int<br/>top_medicines: array<br/>top_diagnoses: array]

    subgraph Indexes["🔍 Indexes for Performance"]
        I1[audit_logs:<br/>- timestamp desc<br/>- user.id, timestamp<br/>- resource.type, timestamp]

        I2[visit_history:<br/>- patient.id, visit_date<br/>- visit_id unique<br/>- doctor.id, visit_date]

        I3[stock_movements:<br/>- medicine.id, timestamp<br/>- timestamp desc<br/>- movement_type, timestamp]

        I4[daily_summaries:<br/>- date unique desc]
    end

    C1 -.->|Indexed by| I1
    C2 -.->|Indexed by| I2
    C3 -.->|Indexed by| I3
    C4 -.->|Indexed by| I4

    subgraph Reports["📈 Reports API"]
        R1[GET /reports/audit-logs<br/>Filter by date, user, action]
        R2[GET /reports/visit-history<br/>Patient visit history]
        R3[GET /reports/stock-movements<br/>Inventory audit trail]
        R4[GET /reports/daily-summary<br/>Daily statistics]
    end

    C1 --> R1
    C2 --> R2
    C3 --> R3
    C4 --> R4

    R1 --> Analytics[📊 Analytics Dashboard]
    R2 --> Analytics
    R3 --> Analytics
    R4 --> Analytics

    style C1 fill:#00bcd4
    style C2 fill:#00bcd4
    style C3 fill:#00bcd4
    style C4 fill:#00bcd4
```

### Audit Log Examples

```mermaid
flowchart TD
    Examples[Audit Log Use Cases] --> UC1[User Management]
    Examples --> UC2[Patient Data Changes]
    Examples --> UC3[Billing & Payments]
    Examples --> UC4[Security Events]

    UC1 --> AL1[Log:<br/>Action: USER_CREATED<br/>User: admin@clinic.com<br/>Resource: New user Dr. Smith<br/>Details: Role DOCTOR assigned]

    UC2 --> AL2[Log:<br/>Action: PATIENT_UPDATED<br/>User: reception@clinic.com<br/>Resource: Patient ID 123<br/>Changes: Phone number updated<br/>Old: 555-0001<br/>New: 555-0002]

    UC3 --> AL3[Log:<br/>Action: PAYMENT_RECEIVED<br/>User: reception@clinic.com<br/>Resource: Invoice INV-001<br/>Details: Amount $49.56<br/>Method: CARD]

    UC4 --> AL4[Log:<br/>Action: LOGIN_FAILED<br/>User: unknown<br/>IP: 192.168.1.100<br/>Reason: Invalid credentials<br/>Attempts: 3]

    style AL1 fill:#00bcd4
    style AL2 fill:#00bcd4
    style AL3 fill:#00bcd4
    style AL4 fill:#00bcd4
```

---

## Database Schema (ER Diagram)

### Complete Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ APPOINTMENTS : "doctor creates"
    USERS ||--o{ VISITS : "doctor conducts"
    USERS ||--o{ SLOTS : "doctor has"
    USERS ||--o{ PRESCRIPTIONS : "doctor writes"
    USERS ||--o{ DISPENSING : "pharmacist dispenses"
    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        enum role "ADMIN,DOCTOR,PHARMACIST,RECEPTION"
        string full_name
        string phone
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    PATIENTS ||--o{ APPOINTMENTS : "books"
    PATIENTS ||--o{ VISITS : "has"
    PATIENTS ||--o{ PRESCRIPTIONS : "receives"
    PATIENTS ||--o{ INVOICES : "billed to"
    PATIENTS {
        int id PK
        string name
        string phone UK
        string email
        date date_of_birth
        enum gender
        string address
        json allergies "[]"
        json chronic_conditions "[]"
        string emergency_contact_name
        string emergency_contact_phone
        timestamp created_at
        timestamp updated_at
    }

    SLOTS ||--o{ APPOINTMENTS : "used in"
    SLOTS {
        int id PK
        int doctor_id FK
        date date
        time start_time
        time end_time
        int duration_minutes
        boolean is_blocked
        string block_reason
        timestamp created_at
    }

    APPOINTMENTS ||--o| VISITS : "converts to"
    APPOINTMENTS {
        int id PK
        int patient_id FK
        int slot_id FK
        enum status "SCHEDULED,CHECKED_IN,WITH_DOCTOR,COMPLETED,CANCELLED"
        string reason_for_visit
        string notes
        timestamp created_at
        timestamp updated_at
    }

    VISITS ||--|| PRESCRIPTIONS : "generates"
    VISITS ||--o{ CLINICAL_NOTES : "contains"
    VISITS {
        int id PK
        int patient_id FK
        int doctor_id FK
        int appointment_id FK "nullable"
        json vitals "bp,temp,pulse,weight,height,spo2"
        string chief_complaint
        string diagnosis
        string treatment_plan
        enum status "IN_PROGRESS,COMPLETED,CANCELLED"
        timestamp started_at
        timestamp completed_at
    }

    CLINICAL_NOTES {
        int id PK
        int visit_id FK
        enum category "SYMPTOM,OBSERVATION,DIAGNOSIS,TREATMENT"
        text note_text
        timestamp created_at
    }

    PRESCRIPTIONS ||--o{ PRESCRIPTION_ITEMS : "contains"
    PRESCRIPTIONS ||--o| INVOICES : "billed in"
    PRESCRIPTIONS ||--o| DISPENSING : "dispensed as"
    PRESCRIPTIONS {
        int id PK
        int visit_id FK
        int patient_id FK
        int doctor_id FK
        boolean dispensed
        timestamp created_at
    }

    MEDICINES ||--o{ PRESCRIPTION_ITEMS : "prescribed in"
    MEDICINES ||--o{ MEDICINE_BATCHES : "stocked as"
    MEDICINES {
        int id PK
        string name UK
        string generic_name
        string manufacturer
        decimal unit_price
        int reorder_level
        string dosage_form "tablet,syrup,injection"
        timestamp created_at
    }

    PRESCRIPTION_ITEMS {
        int id PK
        int prescription_id FK
        int medicine_id FK
        string dosage "500mg"
        string frequency "twice daily"
        int duration_days
        string instructions "after meals"
    }

    MEDICINE_BATCHES ||--o{ DISPENSING_ITEMS : "dispensed from"
    MEDICINE_BATCHES {
        int id PK
        int medicine_id FK
        string batch_number UK
        int quantity
        date expiry_date
        decimal cost_price
        string supplier
        timestamp created_at
        timestamp updated_at
    }

    INVOICES ||--o{ INVOICE_ITEMS : "contains"
    INVOICES ||--o| DISPENSING : "triggers"
    INVOICES {
        int id PK
        string invoice_number UK
        int patient_id FK
        int prescription_id FK "nullable"
        enum mode "AUTO,MANUAL"
        decimal subtotal
        decimal discount
        decimal tax
        decimal total
        enum status "DRAFT,PENDING,PAID,CANCELLED"
        enum payment_method "CASH,CARD,UPI"
        timestamp paid_at
        timestamp created_at
    }

    INVOICE_ITEMS {
        int id PK
        int invoice_id FK
        string item_name
        int quantity
        decimal unit_price
        decimal total_price
    }

    DISPENSING ||--o{ DISPENSING_ITEMS : "contains"
    DISPENSING {
        int id PK
        int prescription_id FK
        int invoice_id FK
        int pharmacist_id FK
        timestamp dispensed_at
    }

    DISPENSING_ITEMS {
        int id PK
        int dispensing_id FK
        int medicine_id FK
        int batch_id FK
        int quantity
        decimal unit_price
    }
```

### Table Relationships Summary

```mermaid
flowchart TD
    subgraph Core["Core Entities"]
        Users[USERS<br/>All system users]
        Patients[PATIENTS<br/>Clinic patients]
    end

    subgraph Appointment["Appointment System"]
        Slots[SLOTS<br/>Doctor availability]
        Appointments[APPOINTMENTS<br/>Bookings]
    end

    subgraph Clinical["Clinical Workflow"]
        Visits[VISITS<br/>Consultations]
        Notes[CLINICAL_NOTES<br/>Visit notes]
        Prescriptions[PRESCRIPTIONS<br/>Rx records]
        PxItems[PRESCRIPTION_ITEMS<br/>Medicines list]
    end

    subgraph Inventory["Inventory System"]
        Medicines[MEDICINES<br/>Medicine catalog]
        Batches[MEDICINE_BATCHES<br/>Stock batches]
    end

    subgraph Financial["Financial System"]
        Invoices[INVOICES<br/>Bills]
        InvoiceItems[INVOICE_ITEMS<br/>Bill details]
    end

    subgraph Pharmacy["Pharmacy"]
        Dispensing[DISPENSING<br/>Dispensing records]
        DispenseItems[DISPENSING_ITEMS<br/>Items dispensed]
    end

    Users --> Slots
    Users --> Visits
    Users --> Prescriptions
    Users --> Dispensing

    Patients --> Appointments
    Patients --> Visits
    Patients --> Prescriptions
    Patients --> Invoices

    Slots --> Appointments
    Appointments --> Visits
    Visits --> Notes
    Visits --> Prescriptions
    Prescriptions --> PxItems

    Medicines --> PxItems
    Medicines --> Batches

    Prescriptions --> Invoices
    Invoices --> InvoiceItems
    Invoices --> Dispensing

    Batches --> DispenseItems
    Dispensing --> DispenseItems

    style Core fill:#e3f2fd
    style Appointment fill:#f3e5f5
    style Clinical fill:#e8f5e9
    style Inventory fill:#fff3e0
    style Financial fill:#fce4ec
    style Pharmacy fill:#e0f2f1
```

---

## End of Document

**Generated for:** Qure Clinic Management System
**Date:** 2026-02-17
**Purpose:** Technical Documentation & System Architecture

---

### How to Use This Document

1. **Convert to PDF:**
   ```bash
   # Using Pandoc
   pandoc FLOWCHARTS.md -o FLOWCHARTS.pdf --pdf-engine=wkhtmltopdf

   # Or using online tools
   # - https://md2pdf.netlify.app/
   # - https://www.markdowntopdf.com/
   ```

2. **Take Screenshots:**
   - Open in a Mermaid-compatible viewer
   - Take high-quality screenshots of each diagram
   - Add to main README as images

3. **Embed in Documentation:**
   - Use for training materials
   - Include in technical specifications
   - Share with development team
