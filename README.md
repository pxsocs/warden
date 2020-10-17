# Welcome to WARden implementation for Specter Server

[![GitHub release](https://img.shields.io/github/release/pxsocs/specter_warden.svg)](https://GitHub.com/pxsocs/specter_warden/releases/)
[![Open Source? Yes!](https://badgen.net/badge/Open%20Source%20%3F/Yes%21/blue?icon=github)](https://GitHub.com/pxsocs/specter_warden/releases/)
[![Powered by NGU](https://img.shields.io/badge/Powered%20by-NGU%20Technology-orange.svg)](https://bitcoin.org)

This is a light weight version of the original WARden designed for integration with Specter Server.

Transactions will be imported automatically from Specter.

This app was built with a couple of goals:

- Easily track portfolio values in fiat (private requests through Tor)
- Monitor Wallets and Addresses for activity using your own node and notify user.
- Track your full node status

> warden (wɔːʳdən )
> A warden is responsible for making sure that the laws or regulations are obeyed.

## Installation

### Please note that the WARden needs to be installed at the same machine running Specter Server.

Installation instructions for Specter can be found [here](https://github.com/cryptoadvance/specter-desktop).

Log in to your computer running Specter, open Terminal and type:

```bash
sudo git clone https://github.com/pxsocs/specter_warden
cd specter_warden
source ./warden_upgrade.sh
```

Then run the WARden server:

```bash
sudo ./warden.sh
```

Open your browser and navigate to:
`http://localhost:25442/`

## Upgrade

From the WARden directory, type:

```bash
 source ./warden_upgrade.sh
```

## This is an Open Source project

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

We believe Open Source is the future of development for bitcoin. There is no other way when transparency and privacy are critical.

The code is not compiled and it can be easily audited.

### Sats for Features

As interest for the app grows and if the community contributes, new features will be added like:
. Import of other transactions
. Editing of transactions
. Enhanced statistics - volatility, compare performance, heatmaps, ...
. Specter implementation without MyNode
. Email notifications
. And suggested improvements

But the app is also open source so anyone can contribute. Anyone looking to contribute / get a bounty is welcome.

## Privacy

Most portfolio tracking tools ask for personal information and may track your IP and other information. Our experience is that even those who say they don't, may have log files at their systems that do track your IP and could be easily linked to your data.

### Why NAV is important?

NAV is particularly important to anyone #stackingsats since it tracks performance relative to current capital allocated.
For example, a portfolio going from $100 to $200 may seem like it 2x but the performance really depends if any new capital was invested or divested during this period. **NAV adjusts for cash inflows and outflows.**

## NAV Tracking

NAV tracks performance based on amount of capital allocated. For example, a portfolio starts at $100.00 on day 0. On day 1, there is a capital inflow of an additional $50.00. Now, if on day 2, the Portfolio value is $200, it's easy to conclude that there's a $50.00 profit. But in terms of % appreciation, there are different ways to calculate performance.
CB Calculates a daily NAV (starting at 100 on day zero).
In this example:

| Day | Portfolio Value\* | Cash Flow  | NAV | Performance |
| --- | ----------------- | ---------- | --- | ----------- |
| 0   | \$0.00            | + \$100.00 | 100 | --          |
| 1   | \$110.00          | + \$50.00  | 110 | +10.00% (1) |
| 2   | \$200.00          | None       | 125 | +25.00% (2) |

> - Portfolio Market Value at beginning of day
>   (1) 10% = 110 / 100 - 1
>   (2) 25% = 200 / (110 + 50) - 1

Tracking NAV is particularly helpful when #stackingsats. It calculates performance based on capital invested at any given time. A portfolio starting at $100 and ending at $200 at a given time frame, at first sight, may seem like is +100% but that depends entirely on amount of capital invested
along that time frame.

### Troubleshooting

> If you get a message telling you that pip is not installed:

```bash
sudo apt-get -y install python3-pip
```

> If you get a message that git was not found:

```bash

sudo apt-get install git
```

**Please note that this is ALPHA software. There is no guarantee that the
information and analytics are correct. Also expect no customer support. Issues are encouraged to be raised through GitHub but they will be answered on a best efforts basis.**
