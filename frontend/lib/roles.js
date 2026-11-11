export const roles = [
  { id: 'learner', label: 'Learner', description: 'See your account, invoices, and history.', views: ['My account', 'Fees'] },
  { id: 'instructor', label: 'Instructor', description: 'Explore programmes, terms, and class rosters.', views: ['Roster', 'Fees'] },
  { id: 'academic_admin', label: 'Academic administrator', description: 'Manage enrolments, scholarships, and academic records.', views: ['Dashboard', 'Students', 'Setup', 'Fees', 'Exceptions'] },
  { id: 'support_staff', label: 'Finance & support', description: 'Review accounts and record payments and refunds.', views: ['Dashboard', 'Students', 'Fees', 'Exceptions'] },
  { id: 'platform_admin', label: 'Platform administrator', description: 'Access the complete workspace and reconciliation.', views: ['Dashboard', 'Students', 'Setup', 'Fees', 'Exceptions'] },
];

export function roleDetails(id) {
  return roles.find(role => role.id === id);
}

export function prepareEntry(role, studentId) {
  if (!roleDetails(role)) return { error: 'Please choose a role to continue.' };
  const id = studentId.trim().toUpperCase();
  if (role === 'learner' && !/^STU-\d{6,}$/.test(id)) {
    return { error: 'Enter a student ID in the format STU-000001.' };
  }
  return { role, studentId: role === 'learner' ? id : '' };
}
