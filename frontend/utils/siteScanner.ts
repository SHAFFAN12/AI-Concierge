export interface NavLink {
    label: string;
    url: string;
}

export const scanSiteNavigation = (): NavLink[] => {
    if (typeof window === 'undefined') return [];

    const links: NavLink[] = [];
    const seenUrls = new Set<string>();
    const currentDomain = window.location.hostname;

    // Selectors for common navigation elements
    const selectors = [
        'nav a',
        'header a',
        '.menu a',
        '.nav a',
        '.navigation a',
        '#menu a',
        '#nav a'
    ];

    const elements = document.querySelectorAll(selectors.join(','));

    elements.forEach((el) => {
        const anchor = el as HTMLAnchorElement;
        const url = anchor.href;
        const label = anchor.innerText.trim();

        // Filter out empty labels, javascript: links, and external links (optional)
        if (
            label &&
            url &&
            !url.startsWith('javascript:') &&
            !url.startsWith('mailto:') &&
            !url.startsWith('tel:') &&
            !seenUrls.has(url)
        ) {
            // Check if it's internal (same domain)
            try {
                const urlObj = new URL(url);
                if (urlObj.hostname === currentDomain) {
                    seenUrls.add(url);
                    links.push({ label, url });
                }
            } catch (e) {
                // Ignore invalid URLs
            }
        }
    });

    return links.slice(0, 50); // Limit to 50 links to avoid overwhelming the context
};
