beforeAll(() => {
    require('../../app/assets/javascripts/stick-to-window-when-scrolling.js');
    require("../../app/assets/javascripts/recalculateStickinessOnMutation.js");
});

afterAll(() => {
  require("./support/teardown.js");
});

const htmlContent = `
<main class="govuk-main-wrapper">
    <div class="ajax-block-container">
        <div class="keyline-block">
            <label>Label</label>
        </div>
        <div class="keyline-block">
            <label>Label</label>
        </div>
        <div class="keyline-block">
            <label>Label</label>
        </div>
        <div class="keyline-block">
            <label>Label</label>
        </div>
    </div>
    <div class="page-footer js-stick-at-bottom-when-scrolling">
        <label>Label</label>
    </div>
</main>
`;

describe("GOVUK.stickAtBottomWhenScrolling.recalculate", () => {
  beforeEach(() => {
    document.body.innerHTML = htmlContent;
    window.GOVUK.addRecalculateStickinessOnMutation()
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("called when '.keyline-block' removed from DOM", (done) => {
    window.GOVUK.stickAtBottomWhenScrolling.init();

    const recalculateSpy = jest.spyOn(window.GOVUK.stickAtBottomWhenScrolling, 'recalculate');

    const keylineBlocks = document.querySelectorAll('.keyline-block');
    const count = keylineBlocks.length;
    keylineBlocks.forEach((block) => {
        block.remove();
    })

    setTimeout(() => {
        expect(recalculateSpy).toHaveBeenCalledTimes(count);
        done();
    }, 0);
  });
});
