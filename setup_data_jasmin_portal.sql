-- This SQL script sets up initial data for the Jasmin Portal, 3 users, 2 resources, 1 consortium, 2 categories, 3 tags, 2 projects, 2 services, 2 requirements, 2 collaborators, and 2 quotas.
-- USE THIS COMMAND FOR SETING THIS DATA (inside venv): python manage.py dbshell < setup_data_jasmin_portal.sql

-- Clear existing data (if any)
DELETE FROM jasmin_manage_requirement;
DELETE FROM jasmin_manage_service;
DELETE FROM jasmin_manage_quota;
DELETE FROM jasmin_manage_collaborator;
DELETE FROM jasmin_manage_invitation;
DELETE FROM jasmin_manage_project_tags;
DELETE FROM jasmin_manage_project;
DELETE FROM jasmin_manage_tag;
DELETE FROM jasmin_manage_category_resources;
DELETE FROM jasmin_manage_category;
DELETE FROM jasmin_manage_resource;
DELETE FROM jasmin_manage_consortium;
DELETE FROM auth_user WHERE username IN ('user1', 'manager1', 'staff1');

-- Create users
INSERT INTO auth_user (password, last_login, is_superuser, username, last_name, email, is_staff, is_active, date_joined, first_name)
VALUES 
('pbkdf2_sha256$260000$pFYt4cjTRqVNSZ9lV8WAuf$JTbSIQT2zxHk6K5zGVvbdOVQMw80Bz9BZKDUfR5M8m8=', NULL, 0, 'user1', 'One', 'user1@example.com', 0, 1, '2025-06-20 10:00:00', 'User'),
('pbkdf2_sha256$260000$pFYt4cjTRqVNSZ9lV8WAuf$JTbSIQT2zxHk6K5zGVvbdOVQMw80Bz9BZKDUfR5M8m8=', NULL, 0, 'manager1', 'One', 'manager1@example.com', 0, 1, '2025-06-20 10:00:00', 'Manager'),
('pbkdf2_sha256$260000$pFYt4cjTRqVNSZ9lV8WAuf$JTbSIQT2zxHk6K5zGVvbdOVQMw80Bz9BZKDUfR5M8m8=', NULL, 0, 'staff1', 'One', 'staff1@example.com', 1, 1, '2025-06-20 10:00:00', 'Staff');

-- Create resources
INSERT INTO jasmin_manage_resource (name, short_name, units, description)
VALUES 
('CPU', 'cpu', 'cores', 'Processor cores'),
('Storage', 'storage', 'GB', 'Disk storage');

-- Create consortium
INSERT INTO jasmin_manage_consortium (name, description, manager_id, is_public, fairshare)
VALUES ('Test Consortium', 'This is a test consortium for tag functionality', 
        (SELECT id FROM auth_user WHERE username = 'manager1'), 1, 100);

-- Create categories
INSERT INTO jasmin_manage_category (name, description, is_public)
VALUES ('Computing', 'Computing resources', 1);

-- Link categories to resources
INSERT INTO jasmin_manage_category_resources (category_id, resource_id)
VALUES 
((SELECT id FROM jasmin_manage_category WHERE name = 'Computing'), 
 (SELECT id FROM jasmin_manage_resource WHERE name = 'CPU')),
((SELECT id FROM jasmin_manage_category WHERE name = 'Computing'), 
 (SELECT id FROM jasmin_manage_resource WHERE name = 'Storage'));

-- Create tags
INSERT INTO jasmin_manage_tag (name)
VALUES ('climate'), ('weather'), ('data-analysis');

-- Create projects
INSERT INTO jasmin_manage_project (name, description, status, created_at, consortium_id, fairshare)
VALUES 
('Climate Research', 'Research project studying climate patterns', 20, '2025-06-20 10:00:00', 
 (SELECT id FROM jasmin_manage_consortium WHERE name = 'Test Consortium'), 1),
('Weather Forecasting', 'Project focused on weather prediction models', 20, '2025-06-20 10:00:00', 
 (SELECT id FROM jasmin_manage_consortium WHERE name = 'Test Consortium'), 1);

-- Link projects to tags
INSERT INTO jasmin_manage_project_tags (project_id, tag_id)
VALUES 
((SELECT id FROM jasmin_manage_project WHERE name = 'Climate Research'), 
 (SELECT id FROM jasmin_manage_tag WHERE name = 'climate')),
((SELECT id FROM jasmin_manage_project WHERE name = 'Climate Research'), 
 (SELECT id FROM jasmin_manage_tag WHERE name = 'data-analysis')),
((SELECT id FROM jasmin_manage_project WHERE name = 'Weather Forecasting'), 
 (SELECT id FROM jasmin_manage_tag WHERE name = 'weather'));

-- Create services
INSERT INTO jasmin_manage_service (name, category_id, project_id)
VALUES 
('data-processing', 
 (SELECT id FROM jasmin_manage_category WHERE name = 'Computing'), 
 (SELECT id FROM jasmin_manage_project WHERE name = 'Climate Research')),
('model-training', 
 (SELECT id FROM jasmin_manage_category WHERE name = 'Computing'), 
 (SELECT id FROM jasmin_manage_project WHERE name = 'Weather Forecasting'));

-- Create requirements
INSERT INTO jasmin_manage_requirement (status, amount, start_date, end_date, created_at, resource_id, service_id, location)
VALUES 
(10, 8, '2025-06-20', '2026-06-20', '2025-06-20 10:00:00', 
 (SELECT id FROM jasmin_manage_resource WHERE name = 'CPU'), 
 (SELECT id FROM jasmin_manage_service WHERE name = 'data-processing'), 'TBC'),
(10, 1000, '2025-06-20', '2026-06-20', '2025-06-20 10:00:00', 
 (SELECT id FROM jasmin_manage_resource WHERE name = 'Storage'), 
 (SELECT id FROM jasmin_manage_service WHERE name = 'data-processing'), 'TBC');

-- Create collaborators
INSERT INTO jasmin_manage_collaborator (role, created_at, project_id, user_id)
VALUES 
(20, '2025-06-20 10:00:00', 
 (SELECT id FROM jasmin_manage_project WHERE name = 'Climate Research'), 
 (SELECT id FROM auth_user WHERE username = 'user1')),
(40, '2025-06-20 10:00:00', 
 (SELECT id FROM jasmin_manage_project WHERE name = 'Climate Research'), 
 (SELECT id FROM auth_user WHERE username = 'manager1'));

-- Create quotas
INSERT INTO jasmin_manage_quota (amount, consortium_id, resource_id)
VALUES 
(100, 
 (SELECT id FROM jasmin_manage_consortium WHERE name = 'Test Consortium'), 
 (SELECT id FROM jasmin_manage_resource WHERE name = 'CPU')),
(10000, 
 (SELECT id FROM jasmin_manage_consortium WHERE name = 'Test Consortium'), 
 (SELECT id FROM jasmin_manage_resource WHERE name = 'Storage'));

-- Pass: Qht24K9hRD