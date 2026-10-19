/**
 * Google Apps Script collector for the gaze-cueing task.
 *
 * Setup (5 minutes, free, no server):
 *  1. Create a new Google Sheet (e.g. "gaze-cueing data").
 *  2. Extensions > Apps Script. Delete the default code, paste this file, save.
 *  3. Deploy > New deployment > Type: Web app.
 *       Description: gaze-cueing collector
 *       Execute as: Me
 *       Who has access: Anyone
 *     Click Deploy, authorise the script, copy the Web app URL (ends with /exec).
 *  4. Give participants the task link with that URL as dataUrl, e.g.
 *       https://mehdi-lahrach.github.io/gaze-cueing-captcha/?study=students-oct2026&dataUrl=https://script.google.com/macros/s/XXXX/exec
 *     or paste the URL into DEFAULTS.dataUrl in index.html so the link stays short.
 *
 * Every finished run appends one row per trial to the "trials" sheet and one row per participant
 * to the "sessions" sheet (with the whole record as JSON). Re-deploy (Manage deployments > edit > new version)
 * after any change to this script.
 */

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);                       // serialise concurrent submissions from a classroom
  try {
    const rec = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const trials = ss.getSheetByName('trials') || ss.insertSheet('trials');
    const sessions = ss.getSheetByName('sessions') || ss.insertSheet('sessions');
    const now = new Date().toISOString();

    const rows = rec.trials || [];
    if (rows.length) {
      let cols;
      if (trials.getLastRow() === 0) {
        cols = Object.keys(rows[0]);
        trials.appendRow(['received_at'].concat(cols));
      } else {
        cols = trials.getRange(1, 2, 1, trials.getLastColumn() - 1).getValues()[0];   // keep the existing header order
      }
      const values = rows.map(r => [now].concat(cols.map(c => (r[c] === null || r[c] === undefined) ? '' : r[c])));
      trials.getRange(trials.getLastRow() + 1, 1, values.length, values[0].length).setValues(values);
    }

    if (sessions.getLastRow() === 0) {
      sessions.appendRow(['received_at', 'pid', 'study', 'code', 'start', 'end', 'n_trials', 'accuracy',
                          'effect_ms', 'untrusted_presses', 'refresh_hz', 'viewport', 'user_agent', 'raw_json']);
    }
    const s = rec.summary || {}, se = rec.session || {}, env = se.env || {};
    const raw = JSON.stringify(rec);
    sessions.appendRow([now, se.pid || '', se.study || '', se.code || '', se.start || '', se.end || '',
                        s.nTrials, s.accuracy, (s.rows && s.rows[0]) ? s.rows[0].effect : '',
                        s.untrustedPresses, env.refresh_hz || '', (env.viewport_w || '') + 'x' + (env.viewport_h || ''),
                        env.ua || '', raw.length < 45000 ? raw : 'record too large for one cell; see trials sheet']);

    return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: String(err) })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return ContentService.createTextOutput('gaze-cueing collector is running');
}
