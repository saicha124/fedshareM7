# DPSShare Algorithm - Differential Privacy with Secret Sharing

## Overview

DPSShare (Differential Privacy with Secret Sharing) is an advanced federated learning algorithm that combines multiple security mechanisms to ensure privacy-preserving distributed machine learning across medical facilities. The algorithm integrates Ciphertext-Policy Attribute-Based Encryption (CP-ABE), differential privacy, secret sharing, and Proof-of-Work (PoW) challenges to create a robust and secure federated learning framework.

## Algorithm Phases

### 2.4.1 Initialization Phase

In the initialization phase, the Trusted Authority (TA) creates the foundation of the federated learning framework. The TA executes the setup procedure of Ciphertext-Policy Attribute-Based Encryption (CP-ABE), generating a public key (PK) and a master secret key (MSK). The public key is shared with all participants, while the master secret key is kept strictly confidential by the TA.

At the same time, the TA defines the set of registered medical facilities U and establishes the attribute universe A, which contains categorical descriptors such as role, institution type, or region. These attributes later control which participants are allowed to access and decrypt the distributed models. The process can be summarized by the following equation:

```
Setup(1^k, U, A) → (PK, MSK)
```

where k is the system's security parameter, U represents the set of facilities, and A denotes the attribute universe.

#### Proof-of-Work Registration

Once the setup is complete, the TA generates a private decryption key for each registered facility based on its attributes. This guarantees that only facilities meeting specific attribute-based policies can decrypt encrypted models in the later phases.

To prevent malicious entities from flooding the system with fake identities (Sybil attacks) or spamming registration requests, every facility must solve a Proof-of-Work (PoW) challenge before registration. The PoW mechanism requires the facility to compute a valid nonce that, when hashed with its identity and public key, produces a digest below a predefined difficulty target:

```
H(nonce ∥ Facility_ID ∥ PK) ≤ Target
```

Here, H represents a secure hash function, nonce is the random number adjusted by the facility, Facility_ID is its unique identifier, and PK is the system's public key. The Target defines the difficulty level chosen by the TA.

**Algorithm 1: System Setup by Trusted Authority (TA)**
```
Input: Security parameter λ, set of facilities U, attribute universe A
Output: Public Key PK, Master Secret Key MSK

1: (PK, MSK) ← Setup(λ, U, A)
2: TA securely stores MSK and distributes PK to all registered facilities
3: Define attribute-based access policies for model decryption
```

**Algorithm 2: Facility Registration with Proof-of-Work**
```
Input: Facility request Req, difficulty parameter D
Output: Verified facility F and issued secret keys

1: Facility solves PoW challenge: Nonce ← FindNonce(H(Req||Nonce) < D)
2: if PoW verified by TA then
3:     TA issues secret key SK_facility based on CP-ABE attributes
4:     Register facility in system database
5: end if
```

### 2.4.2 Model Distribution

After initialization, the Trusted Authority (TA) prepares and distributes the initial machine learning model across the federation in a secure and controlled manner. The TA encrypts the global model using Ciphertext-Policy Attribute-Based Encryption (CP-ABE), ensuring that only facilities whose attributes satisfy the access policy can decrypt and use the model:

```
Encrypt(Model, PK, T) → CT
```

where Model is the initial global model, PK is the public key from the setup phase, and T is the access policy tree that encodes attribute-based restrictions (e.g., facilitytype = hospital AND region = North).

When a registered facility wishes to obtain the global model, it must first authenticate itself by sending an encrypted request to the Leader Server (randomly selected from among fog nodes):

```
Encrypt(PK_Leader, req) → encryReq
```

Upon receiving encryReq, the leader server decrypts the request to recover req. Once verified, the leader server transmits the CP-ABE ciphertext CT to the requesting facility. Only facilities whose attributes satisfy the policy T can decrypt the ciphertext:

```
Decrypt(CT, SK_user) → Model
```

**Algorithm 3: Initial Model Distribution and Decryption by Facility**
```
Input: Encrypted initial model CT, facility private key SK_facility
Output: Decrypted initial model M_init

1: M_init ← User_Decrypt(CT, SK_facility)
2: Facility uses M_init as the starting point for local training
```

### 2.4.3 Local Training, Differential Privacy, and Secret Sharing

After receiving the encrypted global model from the leader server, each medical facility decrypts it using its private key obtained during system initialization:

```
User_Decrypt(CT, SK_facility) → Model
```

Once the global model is obtained, each facility performs local training on its private dataset D_i for a specified number of epochs E. The result of this computation is an updated local model M_local_i.

To ensure privacy, before sharing, each facility perturbs its local model with differential privacy noise. Using the Gaussian mechanism, the facility computes:

```
M'_local_i = M_local_i + N(0, σ²)
```

**Algorithm 4: Local Training with Differential Privacy**
```
Input: Initial model M_init, local dataset d, learning rate η, number of epochs E, noise scale σ
Output: Differentially private local model M_DP_local

1: for epoch = 1 to E do
2:     Compute gradient: ∇F_i(M_init) using local dataset d
3:     Add DP noise: ∇̃ ← ∇F_i(M_init) + N(0, σ²)
4:     Update model: M_DP_local ← M_init - η∇̃
5: end for
```

**Algorithm 5: Secret Sharing and Broadcast to Validator Committee**
```
Input: Local model M_DP_local, number of fog nodes n
Output: Secret shares S_1, S_2, ..., S_n

1: Divide M_DP_local into n shares using Shamir's Secret Sharing
2: for each share S_i do
3:     Send S_i to validator committee for verification
4: end for
5: Broadcast approved shares to fog nodes
```

### 2.4.4 Validation and Committee Mechanism

After each facility generates shares of its differentially private local model, these shares are sent to the validator committee for integrity verification and authentication before being broadcast to fog nodes. The validator committee ensures Byzantine fault tolerance, Sybil resistance, and trust in the federation.

#### Proof-of-Work for Facility Validation

Before any facility can submit its shares, it must solve a computational puzzle:

```
H(N ∥ ID_facility) < T
```

where H is a cryptographic hash function, N is a nonce, ID_facility is the facility's identity, and T is the system-defined difficulty threshold.

#### Digital Signature Authentication

Each facility signs its shares before sending them to the validator committee:

```
Sign(SK_facility, s_ij) → Sig_i
```

The committee verifies:

```
Verify(PK_facility, s_ij, Sig_i) = True
```

If the verification fails, the share is discarded.

#### Committee Consensus Voting

Once authenticated, the committee validates whether the share is consistent and well-formed. Each committee member C_k casts a binary vote (1 = valid, 0 = invalid):

```
Decision(s_ij) = { 1, if Σ(k=1 to m) Vote_k(s_ij) ≥ m/2 + 1
                  { 0, otherwise
```

where m is the number of committee members.

#### Secure Broadcast

Each share s_ij is transmitted securely to the validator committee for verification. Once validated, the committee members perform the broadcast of approved shares to their respective fog nodes:

```
Broadcast(Committee, s_ij) → FogNode_j
```

This ensures that each fog node j receives the correct and authenticated share s_ij of the differentially private local model.

**After validation, the fog nodes assume the role of regional aggregators.** The fog nodes later use these shares in the partial aggregation phase.

**Algorithm 6: Validator Committee Verification and Broadcast**
```
Input: Share s_ij from facility i for fog node j, facility signature Sig_i
Output: Approved and broadcast share to fog node j

1: Verify PoW: if H(N ∥ ID_facility) ≥ T then reject
2: Verify signature: if Verify(PK_facility, s_ij, Sig_i) ≠ True then reject
3: Committee voting:
4:     for each committee member C_k do
5:         Vote_k(s_ij) ← {0 or 1}
6:     end for
7: if Σ Vote_k(s_ij) ≥ m/2 + 1 then
8:     Sign approved share: Sig_Committee ← Sign(SK_Committee, s_ij)
9:     Broadcast(Committee, s_ij) → FogNode_j
10: end if
```

### 2.4.5 Fog Node Partial Aggregation

After validation, the fog nodes assume the role of regional aggregators. Each fog node collects the verified shares from facilities in its region and performs local aggregation using the FedAvg algorithm:

```
M_fog = (1/n) Σ(i=1 to n) S_i
```

#### Security and Authentication

Before sending, fog nodes attach digital signatures to their partial models. This prevents tampering during transmission and ensures integrity:

```
Verify(Sign_fog_j(M_fog_j)) = True ∀j ∈ {1, ..., n}
```

Only authenticated and validated partial models are accepted.

**Algorithm 7: Fog Node Partial Aggregation**
```
Input: Verified shares S_1..n from facilities in the fog region
Output: Partially aggregated model M_fog

1: Apply FedAvg on received shares: M_fog ← (1/n) Σ(i=1 to n) S_i
2: Send M_fog to leader server for global aggregation
```

### 2.5 Leader Server Aggregation

The leader server, randomly selected from the pool of fog nodes, is responsible for performing the global aggregation. Its primary role is to collect the partial models from fog nodes, verify their authenticity, and compute the updated global model.

#### 2.5.1 Input Retrieval

The leader server retrieves all partial models M_fog_j from the fog nodes according to its assigned index:

```
M_fog = {M_fog_1, M_fog_2, ..., M_fog_n}
```

#### 2.5.2 Verification of Authenticity

Each received model is verified using digital signatures to ensure authenticity and integrity:

```
Verify(Sign_fog_j(M_fog_j)) = True ∀j ∈ {1, ..., n}
```

#### 2.5.3 Global Aggregation

The leader server performs the global aggregation strictly as a summation of all valid fog node contributions:

```
M_global = Σ(j=1 to n) M_fog_j
```

This produces the unified global model, which represents the collective knowledge of all participants.

#### 2.5.4 Global Model Redistribution

After the leader server computes the global aggregation, it distributes the resulting global model to all registered medical facilities:

```
Broadcast = {Index_user1 ∥ M_global, Index_user2 ∥ M_global, ..., Index_usern ∥ M_global}
```

Each facility receives the aggregated global model M_global according to its index. Once received, each facility initializes local training. The model is trained for a specified number of epochs E using the facility's local dataset D_i:

```
M_local_i = M_global - η∇F_i(M_global)
```

where η is the learning rate, F_i(x) is the local loss function for facility i, and ∇ is the gradient operator.

After training, each user divides the updated model into secret shares according to the number of fog nodes n, then sends them for committee validation and subsequent partial aggregation. This broadcast–train–share cycle repeats until the global model M_global converges to its final state.

**Algorithm 8: Leader Server Global Aggregation and Redistribution**
```
Input: Partial models M_fog_1, ..., M_fog_n from fog nodes
Output: Global model M_global distributed to all facilities

1: Collect all partial models from fog nodes
2: for each M_fog_j do
3:     Verify(Sign_fog_j(M_fog_j))
4: end for
5: Global aggregation: M_global ← Σ(j=1 to n) M_fog_j
6: for each facility i do
7:     Broadcast(M_global) → Facility_i
8: end for
```

## Security Features

The DPSShare algorithm provides multiple layers of security:

1. **Ciphertext-Policy Attribute-Based Encryption (CP-ABE)**: Fine-grained access control ensures only authorized facilities can decrypt models
2. **Differential Privacy**: Gaussian noise protects individual facility data from being inferred
3. **Secret Sharing**: Model parameters are split into shares, preventing single-point vulnerabilities
4. **Proof-of-Work (PoW)**: Computational puzzles prevent Sybil attacks and spam
5. **Digital Signatures**: All communications are authenticated to prevent tampering
6. **Committee Consensus**: Byzantine fault tolerance through majority voting
7. **Multi-tier Aggregation**: Fog nodes and leader server create a hierarchical security structure

## Implementation Details

The current implementation uses:
- **Additive Secret Sharing** for numerical stability (instead of Shamir's Secret Sharing)
- **Laplace Mechanism** for differential privacy with configurable epsilon (privacy budget)
- **Flask-based API** for communication between clients, servers, and leader
- **Weighted Averaging** for model aggregation based on dataset sizes
- **TensorFlow** for neural network training
- **HMAC-SHA256** for digital signatures (simplified for demonstration)
- **SHA-256 PoW** with configurable difficulty for Sybil attack prevention

This design ensures both security and practical usability in real-world federated learning scenarios.

### Security Implementation Note

**Important**: The current security implementation is simplified for research and demonstration purposes. In a production deployment:

1. **Key Management**: Private keys should be generated using proper cryptographic key generation (e.g., RSA, ECDSA) and securely stored, not derived deterministically from public identifiers
2. **PKI Infrastructure**: A proper Public Key Infrastructure should be deployed with certificate authorities
3. **Encryption**: CP-ABE encryption for model distribution should use established libraries (e.g., Charm-Crypto)
4. **Authentication**: Consider OAuth 2.0 or similar standards for facility authentication
5. **Key Rotation**: Implement regular key rotation policies
6. **Secure Channels**: Use TLS/SSL for all network communications

The current implementation demonstrates the **workflow and protocol structure** as specified in the algorithm design, providing a foundation that can be extended with production-grade cryptographic libraries.
