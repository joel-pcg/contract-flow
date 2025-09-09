# 🚀 **CONTRACTFLOW - FLUJO COMPLETO DE TESTING**

## 📋 **CONFIGURACIÓN INICIAL**

```bash
# 1. Iniciar servicios Docker
cd /Users/joelgerman/Desktop/ContractFlow
docker-compose up -d

# 2. Verificar servicios activos
docker ps
curl -s http://localhost:8000/api/health | jq
```

---

## 🔐 **1. AUTHENTICATION FLOW**

### **1.1 Registro de Usuario Personal**
```bash
# Crear usuario personal
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "personal-user@contractflow.com",
    "password": "SecurePass123!",
    "full_name": "Juan Personal User",
    "account_type": "personal"
  }'

# ✅ Expect: 201 - Registration successful message
```

### **1.2 Registro de Usuario Business**
```bash
# Crear usuario business (requiere organizations)
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "business-user@contractflow.com", 
    "password": "SecurePass123!",
    "full_name": "María Business Owner",
    "account_type": "business",
    "organizations": "TechCorp Solutions"
  }'

# ✅ Expect: 201 - Registration successful + organization created
```

### **1.3 Verificación de Email**
```bash
# Verificar email (usar código de logs Docker)
curl -X POST "http://localhost:8000/api/auth/verify-email" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "personal-user@contractflow.com",
    "code": "VERIFICATION_CODE_FROM_LOGS"
  }'

# ✅ Expect: 200 - Email verified successfully
```

### **1.4 Login**
```bash
# Login exitoso
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "personal-user@contractflow.com",
    "password": "SecurePass123!"
  }'

# ✅ Expect: 200 - JWT tokens + user data
# 💾 GUARDAR: access_token para siguientes requests
```

### **1.5 Casos Edge - Authentication**
```bash
# ❌ Email duplicado
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "personal-user@contractflow.com",
    "password": "AnotherPass123!",
    "full_name": "Duplicate User",
    "account_type": "personal"
  }'
# ❌ Expect: 400 - Email already registered

# ❌ Login con credenciales incorrectas
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "personal-user@contractflow.com",
    "password": "WrongPassword"
  }'
# ❌ Expect: 401 - Incorrect email or password

# ❌ Business sin organization
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "incomplete-business@contractflow.com",
    "password": "SecurePass123!",
    "full_name": "Incomplete Business",
    "account_type": "business"
  }'
# ❌ Expect: 400 - Organization name is required
```

### **1.6 Password Recovery Flow**
```bash
# Forgot password
curl -X POST "http://localhost:8000/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "personal-user@contractflow.com"
  }'

# Reset password (usar código de logs)
curl -X POST "http://localhost:8000/api/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "personal-user@contractflow.com",
    "code": "RESET_CODE_FROM_LOGS",
    "new_password": "NewSecurePass123!",
    "confirm_password": "NewSecurePass123!"
  }'

# ✅ Expect: 200 - Password updated successfully
```

---

## 👤 **2. USER MANAGEMENT**

### **2.1 Profile Management**
```bash
# 🔑 SET TOKEN (from login response)
TOKEN="YOUR_JWT_TOKEN_HERE"

# Get current user info
curl -X GET "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer $TOKEN"

# Update profile
curl -X PATCH "http://localhost:8000/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Juan Updated Name",
    "phone": "+34 666 777 888"
  }'

# Change password
curl -X PATCH "http://localhost:8000/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "NewSecurePass123!",
    "new_password": "UpdatedPass123!"
  }'
```

### **2.2 Logout**
```bash
# Logout (invalidate token)
curl -X POST "http://localhost:8000/api/users/logout" \
  -H "Authorization: Bearer $TOKEN"

# ✅ Expect: 200 - Logged out successfully
# 🧪 Test: Following requests should return 401
```

---

## 🏢 **3. ORGANIZATION MANAGEMENT**

### **3.1 Organization Info**
```bash
# 🔑 Login business user first
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "business-user@contractflow.com",
    "password": "SecurePass123!"
  }'
# 💾 GUARDAR: business_token

BUSINESS_TOKEN="BUSINESS_JWT_TOKEN"

# Get organization information
curl -X GET "http://localhost:8000/api/organizations/information" \
  -H "Authorization: Bearer $BUSINESS_TOKEN"
```

### **3.2 Organization Dashboard**
```bash
# Get organization dashboard (need org_id from previous response)
ORG_ID="ORGANIZATION_ID_FROM_INFO"

curl -X GET "http://localhost:8000/api/organizations/$ORG_ID/dashboard" \
  -H "Authorization: Bearer $BUSINESS_TOKEN"

# ✅ Expect: Dashboard data with metrics, members
```

### **3.3 Invitation Management**
```bash
# Send invitation
curl -X POST "http://localhost:8000/api/organizations/$ORG_ID/invitations" \
  -H "Authorization: Bearer $BUSINESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "invited-user@contractflow.com",
    "role": "editor",
    "message": "Join our organization!"
  }'

# List pending invitations
curl -X GET "http://localhost:8000/api/organizations/$ORG_ID/invitations" \
  -H "Authorization: Bearer $BUSINESS_TOKEN"

# Cancel invitation (need invitation_id)
INVITATION_ID="INVITATION_ID_FROM_LIST"
curl -X DELETE "http://localhost:8000/api/organizations/$ORG_ID/invitations/$INVITATION_ID" \
  -H "Authorization: Bearer $BUSINESS_TOKEN"
```

### **3.4 Member Management**
```bash
# Change member role (need user_id)
USER_ID="USER_ID_TO_CHANGE"
curl -X PUT "http://localhost:8000/api/organizations/$ORG_ID/members/change-role/$USER_ID" \
  -H "Authorization: Bearer $BUSINESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "viewer"
  }'

# Remove member
curl -X DELETE "http://localhost:8000/api/organizations/$ORG_ID/members/$USER_ID" \
  -H "Authorization: Bearer $BUSINESS_TOKEN"
```

### **3.5 Organization Settings**
```bash
# Get settings
curl -X GET "http://localhost:8000/api/organizations/$ORG_ID/settings" \
  -H "Authorization: Bearer $BUSINESS_TOKEN"

# Update settings
curl -X PUT "http://localhost:8000/api/organizations/$ORG_ID/settings" \
  -H "Authorization: Bearer $BUSINESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "security": {
      "require_2fa": true,
      "password_policy": "strong"
    },
    "notifications": {
      "email_notifications": true,
      "sms_notifications": false
    },
    "storage": {
      "limit_gb": 100
    }
  }'
```

---

## 📄 **4. CONTRACT MANAGEMENT**

### **4.1 Contract Creation**
```bash
# 🔑 Use personal or business token
TOKEN="YOUR_JWT_TOKEN"

# Create contract
curl -X POST "http://localhost:8000/api/contracts/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Acuerdo de Servicios Profesionales",
    "description": "Contrato para servicios de consultoría tecnológica",
    "template_type": "service_agreement",
    "effective_date": "2024-12-20T00:00:00Z",
    "expiration_date": "2025-12-20T00:00:00Z",
    "parties": [
      {
        "party_type": "individual",
        "external_name": "Cliente Externo",
        "external_email": "cliente@external.com",
        "signature_required": true
      }
    ],
    "content": {
      "sections": {
        "title": "ACUERDO DE SERVICIOS PROFESIONALES",
        "text": "Este acuerdo establece los términos y condiciones para la prestación de servicios profesionales.",
        "clauses": [
          "1. El proveedor se compromete a entregar los servicios acordados",
          "2. El cliente se compromete al pago según términos establecidos",
          "3. Ambas partes respetarán la confidencialidad"
        ]
      },
      "change_summary": "Creación inicial del contrato"
    }
  }'

# ✅ Expect: 201 - Contract created
# 💾 GUARDAR: contract_id
```

### **4.2 Contract Retrieval**
```bash
CONTRACT_ID="CONTRACT_ID_FROM_CREATION"

# List contracts
curl -X GET "http://localhost:8000/api/contracts/" \
  -H "Authorization: Bearer $TOKEN"

# Get contract details
curl -X GET "http://localhost:8000/api/contracts/$CONTRACT_ID" \
  -H "Authorization: Bearer $TOKEN"

# Get contract data (for frontend display)
curl -X GET "http://localhost:8000/api/contracts/$CONTRACT_ID/data" \
  -H "Authorization: Bearer $TOKEN"

# Get contracts dashboard
curl -X GET "http://localhost:8000/api/contracts/dashboard" \
  -H "Authorization: Bearer $TOKEN"
```

### **4.3 PDF Generation**
```bash
# Generate and view PDF
curl -X GET "http://localhost:8000/api/contracts/$CONTRACT_ID/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  --output contract.pdf

# Download PDF
curl -X GET "http://localhost:8000/api/contracts/$CONTRACT_ID/pdf?download=true" \
  -H "Authorization: Bearer $TOKEN" \
  --output contract_download.pdf

# PDF with watermark
curl -X GET "http://localhost:8000/api/contracts/$CONTRACT_ID/pdf?watermark=DRAFT" \
  -H "Authorization: Bearer $TOKEN" \
  --output contract_draft.pdf
```

### **4.4 Send for Signature**
```bash
# Send contract for signature
curl -X POST "http://localhost:8000/api/contracts/$CONTRACT_ID/send-for-signature" \
  -H "Authorization: Bearer $TOKEN"

# ✅ Expect: 200 - Contract sent, status changed to PENDING
```

---

## ✍️ **5. SIGNATURE WORKFLOW**

### **5.1 Signature Status**
```bash
# Get signature status
curl -X GET "http://localhost:8000/api/signatures/$CONTRACT_ID/signature-status" \
  -H "Authorization: Bearer $TOKEN"

# Get all signatures
curl -X GET "http://localhost:8000/api/signatures/$CONTRACT_ID/signatures" \
  -H "Authorization: Bearer $TOKEN"
```

### **5.2 Contract Signing**
```bash
# Sign contract (NO AUTH REQUIRED - external endpoint)
curl -X POST "http://localhost:8000/api/signatures/$CONTRACT_ID/sign" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "'$CONTRACT_ID'",
    "party_email": "cliente@external.com",
    "signature_method": "digital",
    "signature_data": {
      "full_name": "Cliente Externo",
      "agreed_terms": true
    }
  }'

# ✅ Expect: 201 - Contract signed successfully
```

### **5.3 Request Additional Signatures**
```bash
# Request signatures (resend emails)
curl -X POST "http://localhost:8000/api/signatures/$CONTRACT_ID/request-signatures" \
  -H "Authorization: Bearer $TOKEN"

# ✅ Expect: 200 - Signature requests sent
```

### **5.4 Contract Rejection**
```bash
# Reject contract (NO AUTH REQUIRED - external endpoint)
curl -X POST "http://localhost:8000/api/signatures/$CONTRACT_ID/reject" \
  -H "Content-Type: application/json" \
  -d '{
    "party_email": "cliente@external.com",
    "reason": "Terms not acceptable"
  }'

# ✅ Expect: 200 - Contract rejected, status changed to REJECTED
```

---

## ❌ **6. EDGE CASES & ERROR TESTING**

### **6.1 Unauthorized Access**
```bash
# Access protected endpoint without token
curl -X GET "http://localhost:8000/api/contracts/" 

# ❌ Expect: 401 - Not authenticated

# Access with invalid token
curl -X GET "http://localhost:8000/api/contracts/" \
  -H "Authorization: Bearer invalid_token"

# ❌ Expect: 401 - Invalid token
```

### **6.2 Permission Errors**
```bash
# Access organization endpoints with personal account
curl -X GET "http://localhost:8000/api/organizations/information" \
  -H "Authorization: Bearer $PERSONAL_TOKEN"

# ❌ Expect: 403 - Insufficient permissions
```

### **6.3 Resource Not Found**
```bash
# Access non-existent contract
curl -X GET "http://localhost:8000/api/contracts/00000000-0000-0000-0000-000000000000" \
  -H "Authorization: Bearer $TOKEN"

# ❌ Expect: 404 - Contract not found
```

### **6.4 Validation Errors**
```bash
# Create contract with missing required fields
curl -X POST "http://localhost:8000/api/contracts/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Incomplete Contract"
  }'

# ❌ Expect: 422 - Validation errors

# Sign contract with wrong email
curl -X POST "http://localhost:8000/api/signatures/$CONTRACT_ID/sign" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "'$CONTRACT_ID'",
    "party_email": "wrong@email.com",
    "signature_method": "digital"
  }'

# ❌ Expect: 400 - Party not found or not authorized
```

---

## 🧹 **7. CLEANUP**
```bash
# Stop Docker services
docker-compose down

# Remove test files
rm -f contract*.pdf
```

---

## 📊 **RESUMEN DE TESTING**

### **✅ Endpoints Probados: 25+**
- **Authentication**: 6 endpoints
- **User Management**: 5 endpoints  
- **Organizations**: 8 endpoints
- **Contracts**: 6 endpoints
- **Signatures**: 5 endpoints

### **🧪 Casos de Uso Cubiertos:**
- ✅ Flujo completo de registro y verificación
- ✅ Gestión de organizaciones y miembros
- ✅ Creación y gestión de contratos
- ✅ Flujo completo de firmas digitales
- ✅ Generación de PDFs
- ✅ Sistema de permisos
- ✅ Validación de errores
- ✅ Casos edge y seguridad

### **🎯 Status Esperados:**
- **2xx**: Operaciones exitosas
- **400**: Errores de validación
- **401**: No autenticado  
- **403**: Sin permisos
- **404**: Recurso no encontrado
- **422**: Errores de validación de datos
- **500**: Errores del servidor
