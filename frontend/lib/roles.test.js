import { test } from 'node:test';
import { deepStrictEqual, ok } from 'node:assert';
import { prepareEntry, roles, roleDetails } from './roles.js';

test('role navigation matches the available workspace permissions', () => {
  deepStrictEqual(roleDetails('learner').views, ['My account', 'Fees']);
  deepStrictEqual(roleDetails('instructor').views, ['Roster', 'Fees']);
  ok(!roleDetails('support_staff').views.includes('Setup'));
  ok(roleDetails('platform_admin').views.includes('Exceptions'));
  ok(roles.every(role => role.views.length > 0));
});

test('entry requires a role and validates learner identity without signing in', () => {
  ok(prepareEntry('', '').error);
  ok(prepareEntry('learner', '').error);
  deepStrictEqual(prepareEntry('learner', ' stu-000001 '), {role: 'learner', studentId: 'STU-000001'});
  deepStrictEqual(prepareEntry('instructor', 'STU-000001'), {role: 'instructor', studentId: ''});
  ok(prepareEntry('unknown', '').error);
});
