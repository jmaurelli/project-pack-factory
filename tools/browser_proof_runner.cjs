#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {};
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--request-file') {
      args.requestFile = argv[index + 1];
      index += 1;
    }
  }
  if (!args.requestFile) {
    throw new Error('--request-file is required');
  }
  return args;
}

function buildAssertion(name, status, summary, extras = {}) {
  return {
    name,
    status,
    summary,
    ...extras,
  };
}

async function main() {
  const { requestFile } = parseArgs(process.argv);
  const request = JSON.parse(fs.readFileSync(requestFile, 'utf8'));
  const { chromium } = require('playwright');
  const browserExecutablePath = chromium.executablePath();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleMessages = [];
  const pageErrors = [];

  if (request.capture_console) {
    page.on('console', (message) => {
      if (consoleMessages.length >= 20) return;
      consoleMessages.push({
        type: message.type(),
        text: message.text(),
      });
    });
  }

  page.on('pageerror', (error) => {
    if (pageErrors.length >= 10) return;
    pageErrors.push(String(error));
  });

  const assertions = [];
  let failureSummary = '';
  let overviewLabel = '';
  let summaryCommandCountText = '';
  let detectedRunBlockCount = 0;
  let initiallyCollapsed = false;
  let detailsOpenAfterNavigation = false;

  try {
    await page.goto(request.target_url, {
      waitUntil: 'domcontentloaded',
      timeout: request.timeout_ms,
    });

    const detailsSelector = `#${request.target_id}`;
    const linkSelector = `a.adf-preview-manual-link[data-adf-manual-target="${request.target_id}"]`;
    const details = page.locator(detailsSelector);
    const overviewLink = page.locator(linkSelector);

    await overviewLink.waitFor({ state: 'visible', timeout: request.timeout_ms });
    const overviewCount = await overviewLink.count();
    assertions.push(
      buildAssertion(
        'overview_link_present',
        overviewCount === 1 ? 'pass' : 'fail',
        overviewCount === 1
          ? `Found overview link for ${request.target_id}.`
          : `Expected one overview link for ${request.target_id}, found ${overviewCount}.`,
      ),
    );

    await details.waitFor({ state: 'attached', timeout: request.timeout_ms });
    overviewLabel = (await overviewLink.locator('strong').innerText()).trim();
    summaryCommandCountText = (await details.locator('.adf-preview-manual-summary-count').innerText()).trim();
    initiallyCollapsed = !(await details.evaluate((element) => Boolean(element.open)));
    assertions.push(
      buildAssertion(
        'target_card_initially_collapsed',
        initiallyCollapsed ? 'pass' : 'fail',
        initiallyCollapsed
          ? 'Target field-manual card starts collapsed before navigation.'
          : 'Target field-manual card was already open before navigation.',
      ),
    );

    const summaryCountMatch = summaryCommandCountText.match(/(\d+)/);
    const summaryCommandCount = summaryCountMatch ? Number.parseInt(summaryCountMatch[1], 10) : Number.NaN;

    await overviewLink.click();
    await page.waitForFunction(
      ({ targetId, pagePath }) => {
        const target = document.getElementById(targetId);
        return (
          window.location.pathname === pagePath &&
          window.location.hash === `#${targetId}` &&
          target instanceof HTMLDetailsElement &&
          target.open === true
        );
      },
      { targetId: request.target_id, pagePath: request.page_path },
      { timeout: request.timeout_ms },
    );

    const finalUrl = page.url();
    const finalHash = new URL(finalUrl).hash;
    detailsOpenAfterNavigation = await details.evaluate((element) => Boolean(element.open));
    assertions.push(
      buildAssertion(
        'hash_navigation_matches_target',
        finalHash === `#${request.target_id}` ? 'pass' : 'fail',
        finalHash === `#${request.target_id}`
          ? `Navigation landed on #${request.target_id}.`
          : `Navigation landed on ${finalHash || '<empty hash>'} instead of #${request.target_id}.`,
      ),
    );
    assertions.push(
      buildAssertion(
        'target_card_opens_after_navigation',
        detailsOpenAfterNavigation ? 'pass' : 'fail',
        detailsOpenAfterNavigation
          ? 'Target field-manual card is open after overview-link navigation.'
          : 'Target field-manual card stayed closed after overview-link navigation.',
      ),
    );

    detectedRunBlockCount = await details.locator('.adf-check').evaluateAll((checks) => {
      return checks.filter((check) =>
        Array.from(check.querySelectorAll('p.adf-inline-label')).some(
          (label) => (label.textContent || '').trim() === 'Run',
        ),
      ).length;
    });

    const countMatches = Number.isInteger(summaryCommandCount) && summaryCommandCount === detectedRunBlockCount;
    assertions.push(
      buildAssertion(
        'summary_command_count_matches_run_blocks',
        countMatches ? 'pass' : 'fail',
        countMatches
          ? `Summary count ${summaryCommandCount} matches detected run blocks.`
          : `Summary count ${summaryCommandCountText} does not match detected run blocks ${detectedRunBlockCount}.`,
        {
          expected_value: summaryCommandCountText,
          actual_value: detectedRunBlockCount,
        },
      ),
    );

    if (request.capture_screenshot_path) {
      await page.screenshot({ path: request.capture_screenshot_path, fullPage: true });
    }

    const status = assertions.every((assertion) => assertion.status === 'pass') ? 'pass' : 'fail';
    if (status !== 'pass') {
      failureSummary = assertions.filter((assertion) => assertion.status !== 'pass').map((assertion) => assertion.summary).join(' ');
    }

    const browserVersion = browser.version();
    await browser.close();
    return {
      status,
      browser_executable_path: browserExecutablePath,
      browser_version: browserVersion,
      overview_label: overviewLabel,
      summary_command_count_text: summaryCommandCountText,
      detected_run_block_count: detectedRunBlockCount,
      initially_collapsed: initiallyCollapsed,
      details_open_after_navigation: detailsOpenAfterNavigation,
      final_url: finalUrl,
      final_hash: finalHash,
      assertions,
      console_message_count: consoleMessages.length,
      console_messages: consoleMessages,
      page_errors: pageErrors,
      failure_summary: failureSummary,
    };
  } catch (error) {
    if (request.capture_screenshot_path) {
      try {
        await page.screenshot({ path: request.capture_screenshot_path, fullPage: true });
      } catch (_captureError) {
      }
    }
    const browserVersion = browser.version();
    await browser.close();
    return {
      status: 'fail',
      browser_executable_path: browserExecutablePath,
      browser_version: browserVersion,
      overview_label: overviewLabel,
      summary_command_count_text: summaryCommandCountText,
      detected_run_block_count: detectedRunBlockCount,
      initially_collapsed: initiallyCollapsed,
      details_open_after_navigation: detailsOpenAfterNavigation,
      final_url: page.url(),
      final_hash: (() => {
        try {
          return new URL(page.url()).hash;
        } catch (_error) {
          return '';
        }
      })(),
      assertions,
      console_message_count: consoleMessages.length,
      console_messages: consoleMessages,
      page_errors: pageErrors,
      failure_summary: String(error),
    };
  }
}

main()
  .then((payload) => {
    process.stdout.write(`${JSON.stringify(payload)}\n`);
    process.exit(payload.status === 'pass' ? 0 : 1);
  })
  .catch((error) => {
    process.stdout.write(
      `${JSON.stringify({
        status: 'fail',
        browser_executable_path: '',
        assertions: [],
        console_message_count: 0,
        console_messages: [],
        page_errors: [],
        failure_summary: String(error),
      })}\n`,
    );
    process.exit(1);
  });
