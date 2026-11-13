# Changelog

## [1.5.1](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/compare/v1.5.0...v1.5.1) (2026-10-21)


### Features

* **diagnostics:** expose cooling capability and heat/cool state ([22cfa8d](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/22cfa8db1eb2683bf5bbbef950701b480094674e))

## [1.5.0](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/compare/v1.4.2...v1.5.0) (2026-10-21)


### Features

* **discovery:** auto-detect reGATE hub via DHCP hostname ([f53b6ba](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/f53b6baf8fd2b289b45a5782fc9f9ed26fe96918))
* **mqtt:** support optional broker username/password ([51742ae](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/51742ae72dd1388d0a57b7b8204a72a70c483896))
* show hub firmware and serial on device page ([b4158cc](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/b4158cc6ad3e3be1c6acca4019693d2274d09d39))


### Bug Fixes

* **climate:** derive heat/cool from system PAC, not room temperature ([3e673b9](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/3e673b9ef00dea3a05fb952db7b84efa284b928e))

## [1.4.2](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/compare/v1.4.1...v1.4.2) (2026-10-19)


### Bug Fixes

* **exceptions:** translate MqttNotConnected message ([76d1e01](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/76d1e01e5dba21c8cd19986eea898dfb32d68946))

## [1.4.1](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/compare/v1.4.0...v1.4.1) (2026-08-31)


### Bug Fixes

* repair runtime_data regressions from the store refactor ([c673223](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/c67322322583524995372d6b133dd6b9525f4f1d))

## [1.4.0](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/compare/v1.3.0...v1.4.0) (2026-08-28)


### Features

* reload on options change, zone availability, i18n parity test ([a649349](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/a649349c20b7a22abd508bc67af702e2b8c2c798))
* telemetry github-label source of truth, sync tooling, migration scaffold ([e211419](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/e2114191ab5a1553a683750829a6e131e15ff596))


### Bug Fixes

* address HACS review feedback ([10ba1e9](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/10ba1e9a07202da58f18312c195faab08eb06484))

## [1.3.0](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/compare/v1.2.4...v1.3.0) (2026-08-12)


### Features

* **config:** add reconfigure flow to edit host/port/prefix ([f22db5b](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/commit/f22db5b8e2541c297ec4383b0009520333348ef2))
