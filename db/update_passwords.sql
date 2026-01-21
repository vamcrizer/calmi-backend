-- Update password hashes for test users
-- New hash for 'password123' using bcrypt directly

UPDATE users 
SET password_hash = '$2b$12$Fo2SSyNK.R6tHpmELnbmH.198bp9NpzFA5kP.V1EpkerOV5gEtQUS'
WHERE username IN ('student01', 'teacher01', 'counselor01', 'schooladmin01');

SELECT username, 'password updated' as status FROM users 
WHERE username IN ('student01', 'teacher01', 'counselor01', 'schooladmin01');
