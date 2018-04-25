"use strict";

let bids = require("../../design/lib/bids");
let assert = require("../../../node_modules/chai").assert;

describe("bids view tests", () => {
    describe("get_eu_tender_bids", () => {
        let tender;

        it("tender qualifications and bids are empty - should return empty array.", () => {
            tender = {
                qualifications: [],
                bids: []
            };

            assert.deepEqual(bids.get_eu_tender_bids(tender), []);
        });

        it("ID's don't match - should return empty array.", () => {
            tender.qualifications.push({
                bidID: "not_bid_id"
            });
            tender.bids.push({
                id: "bid_id"
            });

            assert.deepEqual(bids.get_eu_tender_bids(tender), []);
        });

        it("ID's match - should return array containing bid.", () => {
            tender.qualifications[0].bidID = "bid_id";
            assert.deepEqual(bids.get_eu_tender_bids(tender), tender.bids);
        });
    });

    describe("find_matched_revs", () => {
        const pattern = "/something";
        const antipattern = "/smth_else";
        const date = "2017-11-10T00:00:00Z";
        let revisions;

        it("there are no paths matching pattern - should return empty array.", () => {
            revisions = [
                {
                    date: date,
                    changes: [{
                        path: antipattern,
                        op: "remove"
                    }]
                }
            ];

            assert.deepEqual(bids.find_matched_revs(revisions, pattern), []);
        });

        it("there are paths matching pattern - should return revisions.", () => {
            revisions[0].changes.push({
                path: pattern,
                op: "remove"
            });

            assert.deepEqual(bids.find_matched_revs(revisions, pattern), revisions);
        });
    });

    describe("find_initial_bid_date", () => {
        const bid_index = "bid_index";
        let revisions;

        it("revisions has no changes with '/bids/' path - should return empty string.", () => {
            revisions = [
                {
                    date: "2017-11-13T00:00:00Z",
                    changes: [{
                        path: "/something",
                        op: "remove"
                    }]
                }
            ];

            assert.strictEqual(bids.find_initial_bid_date(revisions), "");
        });

        it("there are '/bids' in changes path - should return first revision date.", () => {
            revisions[0].changes.push({
                path: "/bids",
                op: "remove"
            });

            assert.strictEqual(bids.find_initial_bid_date(revisions), revisions[0].date);
        });

        it("there are '/bids/' + bid_index in changes path - should return first revision date.", () => {
            revisions[0].changes.path += "/" + bid_index;
            assert.strictEqual(bids.find_initial_bid_date(revisions, bid_index), revisions[0].date);
        });
    });

    describe("filter_bids", () => {
        it("should return bids later then 2017-01-01T00:00:00+03:00 with active or invalid.pre-qualification status.", () => {
            let input_bids = [
                {
                    date: "2016-11-13T00:00:00Z",
                    status: "active",
                },
                {
                    date: "2016-11-13T00:00:00Z",
                    status: "invalid.pre-qualification",
                },
                {
                    date: "2017-11-13T00:00:00Z",
                    status: "cancelled",
                },
                {
                    date: "2017-11-13T00:00:00Z",
                    status: "active",
                },
                {
                    date: "2017-11-13T00:00:00Z",
                    status: "invalid.pre-qualification",
                }
            ];

            let expected_bids = [
                {
                    date: "2017-11-13T00:00:00Z",
                    status: "active",
                },
                {
                    date: "2017-11-13T00:00:00Z",
                    status: "invalid.pre-qualification",
                }
            ];

            assert.deepEqual(expected_bids, bids.filter_bids(input_bids));
        });
    });

    describe("find_first_revision_date", () => {
        let tender;

        it("tender has no revisions - should return empty string.", () => {
            tender = {};
            assert.strictEqual(bids.find_first_revision_date(tender), "");
        });

        it("tender revisions is empty array - should return empty string.", () => {
            tender.revisions = [];
            assert.strictEqual(bids.find_first_revision_date(tender), "");
        });

        it("tender has revision with date - should return revision date.", () => {
            tender.revisions.push({
                date: "2017-11-13T00:00:00Z"
            });
            assert.strictEqual(bids.find_first_revision_date(tender), tender.revisions[0].date);
        });
    });

    describe("date_normalize", () => {
        // ???
    });

    describe("count_lot_bids", () => {
        let lot, tender;

        it("tender bids is empty array - should return 0 (length of empty array).", () => {
            lot = {
                id: "lot_id"
            };
            tender = {
                bids : []
            };

            assert.strictEqual(bids.count_lot_bids(lot, tender), 0);
        });

        it("tender has one valid bid - should return 1.", () => {
            tender.bids = [
                {
                    status: "active",
                    date: "2017-11-13T00:00:00Z",
                    lotValues: [
                        {
                            relatedLot: lot.id
                        },
                        {
                            relatedlot: "not_lot_id"
                        }
                    ]
                }
            ];

            assert.strictEqual(bids.count_lot_bids(lot, tender), 1);
        });
    });

    describe("count_lot_qualifications", () => {
        let qualifications, lot;

        it("qualifications is undefined - should return 0.", () => {
            assert.strictEqual(bids.count_lot_qualifications(qualifications), 0);
        });

        it("qualifications is empty array - should return 0.", () => {
            qualifications = [];
            assert.strictEqual(bids.count_lot_qualifications(qualifications), 0);
        });

        it("there is one qualification with lotID matching lot id and valid status - should return 1.", () => {
            lot = {
                status: "cancelled",
                id: "lot_id"
            };

            qualifications.push(
                {
                    status: "active",
                    lotID: lot.id
                },
                {
                    status: "",
                    lotID: lot.id
                },
                {
                    status: "active",
                    lotID: "not_lot_id"
                }
            );

            assert.strictEqual(bids.count_lot_qualifications(qualifications, lot), 1);
        });

        it("there is two qualifications with lotID matching lot id and status is not cancelled - should return 2.", () => {
            lot.status = "active";
            qualifications.push({
                status: "cancelled",
                lotID: lot.id
            });

            assert.strictEqual(bids.count_lot_qualifications(qualifications, lot), 2);
        });
    });

    describe("check_tender", () => {
        let tender;

        it("tender status is undefined - should return true.", () => {
            tender = {
            };
            assert.isTrue(bids.check_tender(tender));
        });

        it("tender status is unsuccessful - should return the result of check_tender_bids", () => {
            tender.status = "unsuccessful";
            tender.awards = [];
            assert.strictEqual(bids.check_tender(tender), bids.check_tender_bids(tender));
        });

        it("tender status is cancelled and tender date is later then bids disclojure date - should return the result of check_tender_bids", () => {
            tender.status = "cancelled";
            tender.qualificationPeriod = {startDate:"2017-01-01T00:00:00Z"};
            tender.date = "2017-11-13T00:00:00Z";
            assert.strictEqual(bids.check_tender(tender), bids.check_tender_bids(tender));
        });

        it("tender status is cancelled and tender date is earlier then bids disclojure date - should return false.", () => {
            tender.status = "cancelled";
            tender.date = "2016-11-13T00:00:00Z";
            assert.isFalse(bids.check_tender(tender));
        });
    });

    describe("check_lot", () => {
        let lot, tender;

        it("lot status is undefined - should return true.", () => {
            lot = {
            };

            assert.isTrue(bids.check_lot(undefined, lot));
        });

        it("lot status is unsuccessful - should return true (the result of check_lot_bids).", () => {
            lot.status = "unseccessful";
            tender = {
                procurementMethodType: "belowThreshold"
            };

            assert.isTrue(bids.check_lot(tender, lot));
        });

        it("lot status is cancelled and lot date is earlier then bids disclojure date - should return false.", () => {
            lot.status = "cancelled";
            tender.qualificationPeriod = {
                startDate: "2017-11-14T00:00:00Z"
            };
            lot.date = "2016-11-14T00:00:00Z";

            assert.isFalse(bids.check_lot(tender, lot));
        });

        it("lot status is cancelled and lot date is not earlier then bids disclojure date - should return true.", () => {
            lot.status = "cancelled";
            lot.date = tender.qualificationPeriod.startDate;
            assert.isTrue(bids.check_lot(tender, lot));
        });
    });

    describe("get_audit", () => {
        let lot, tender, lot_pattern;
        const tender_pattern = "audit";

        it("tender has no documents - should return null.", () => {
            lot = {
                id: "lot_id"
            };
            tender = {
                id: "tender_id"
            };

            lot_pattern = "audit_" + tender.id + "_" + lot.id;

            assert.isNull(bids.get_audit(tender, lot_pattern));
            assert.isNull(bids.get_audit(tender, tender_pattern));
        });

        it("tender has one valid document - should return this document.", () => {
            tender.documents = [{
                title: "audit_" + tender.id + "_" + lot.id
            }];

            assert.deepEqual(tender.documents[0], bids.get_audit(tender, lot_pattern));
            assert.deepEqual(tender.documents[0], bids.get_audit(tender, tender_pattern));
        });

        it("tender has one invalid and one valid documents - should return valid document.", () => {
            tender.documents.splice(0, 0, {
                title: ""
            });
            assert.deepEqual(tender.documents[1], bids.get_audit(tender, lot_pattern));
            assert.deepEqual(tender.documents[1], bids.get_audit(tender, tender_pattern));
        });

        it("tender has two valid documents - should return the one with earlier dateModified.", () => {
            tender.documents[1].dateModified = "2017-11-14T00:00:00Z";
            tender.documents.push({
                title: "audit_" + tender.id + "_" + lot.id,
                dateModified: "2017-11-13T00:00:00Z"
            });

            assert.deepEqual(tender.documents[2], bids.get_audit(tender, lot_pattern));
            assert.deepEqual(tender.documents[2], bids.get_audit(tender, tender_pattern));
        });
    });

    describe("find_lot_for_bid", () => {
        let tender, lotValue;

        it("tender has no lots - should return false.", () => {
            tender = {
                lots: []
            }
            lotValue = {
            }

            assert.isFalse(bids.find_lot_for_bid(tender, lotValue));
        });

        it("tender has no lots matching lotValue id - should return false.", () => {
            tender.lots.push({
                id: "not_lot_id"
            });
            lotValue.relatedLot = "lot_id";

            assert.isFalse(bids.find_lot_for_bid(tender, lotValue));
        });

        it("tender has lots matching lotValue id - should return first of them.", () => {
            tender.lots.push(
                {
                    id: "lot_id",
                    dateModified: "2017-11-14T00:00:00Z"
                },
                {
                    id: "lot_id",
                    dateModified: "2017-11-15T00:00:00Z"
                }
            );

            assert.deepEqual(tender.lots[1], bids.find_lot_for_bid(tender, lotValue));
        });
    });

    describe("check_award_for_bid", () => {
        let tender, bid;
        it("tender has no awards - should return true.", () => {
            tender = {
            };
            bid = {
            };

            assert.isTrue(bids.check_award_for_bid(tender));
        });

        it("tender has no valid awards and no awards in status active or pending - should return true.", () => {
            bid.id = "bid_id";
            tender.awards = [{
                bid_id: "not_bid_id"
            }];

            assert.isTrue(bids.check_award_for_bid(tender, bid));
        });

        it("tender has valid award and no awards in status active or pending - should return false.", () => {
            bid.date = '1970-01-01';
            tender.awards[0].bid_id = bid.id;
            tender.awards[0].date = bid.date;
            assert.isFalse(bids.check_award_for_bid(tender, bid));
        })

        it("tender has valid award and award in status active or pending - should return true.", () => {
            tender.awards[0].status = "active";
            assert.isTrue(bids.check_award_for_bid(tender, bid));
        });

        it("tender has valid award and award in status active or pending - should return true.", () => {
            tender.awards[0].status = "pending";
            assert.isTrue(bids.check_award_for_bid(tender, bid));
        });

        it("tender has no valid awards and has award in status active or pending - should return true.", () => {
            tender.awards[0].bid_id = "not_bid_id";
            tender.status = "active";
            assert.isTrue(bids.check_award_for_bid(tender, bid));
        });

        it("tender has no valid awards and has award in status active or pending - should return true.", () => {
            tender.status = "pending";
            assert.isTrue(bids.check_award_for_bid(tender, bid));
        });
    });

    describe("check_award_for_bid_multilot", () => {
        let tender, bid, lot;

        it("tender has no awards - should return true.", () => {
            tender = {
            };
            bid = {
            };
            lot = {
            };

            assert.isTrue(bids.check_award_for_bid_multilot(tender, bid, lot));
        });

        it("tender has no valid awards - should return true.", () => {
            bid.id = "bid_id";
            lot.id = "lot_id";
            tender.awards = [{
                bid_id: "not_bid_id",
                lotID: "not_lot_id"
            }];

            assert.isTrue(bids.check_award_for_bid_multilot(tender, bid, lot));
        });

        it("tender has valid awards and no awards in status active or pending - should return false.", () => {
            tender.awards[0].bid_id = bid.id;
            tender.awards[0].lotID = lot.id;
            assert.isFalse(bids.check_award_for_bid_multilot(tender, bid, lot));
        });
        
        it("tender has valid awards and awards in status active or pending - should return true.", () => {
            bid.date = '1970-01-01'
            tender.awards[0].status = "active";
            tender.awards[0].date = bid.date;
            assert.isTrue(bids.check_award_for_bid_multilot(tender, bid, lot));
        });

        // if tender has no awards function would return true anyway
    });

    describe("check_qualification_for_bid", () => {
        let tender, bid, lot;

        it("tender has no qualifications - should return false.", () => {
            tender = {
                qualifications: []
            };

            assert.isFalse(bids.check_qualification_for_bid(tender));
        });

        it("tender has no qualifications related to bid - should return false.", () => {
            bid = {
                id: "bid_id"
            };
            tender.qualifications.push({
                bidID: "not_bid_id"
            });

            assert.isFalse(bids.check_qualification_for_bid(tender, bid));
        });

        it("tender has qualification related to bid, but qualification status is not active - should return false.", () => {
            tender.qualifications[0].bidID = bid.id;
            tender.qualifications[0].status = "";
            assert.isFalse(bids.check_qualification_for_bid(tender, bid));
        });

        it("tender has qualification related to bid and qualification status is active - should return true.", () => {
            tender.qualifications[0].status = "active";
            assert.isTrue(bids.check_qualification_for_bid(tender, bid));
        });

        it("tender has no qualifications related to lot - should return false.", () => {
            lot = {
                id: "lot_id"
            }
            tender.qualifications[0].lotID = "not_lot_id";
            assert.isFalse(bids.check_qualification_for_bid(tender, bid, lot));
        });

        it("tender has qualifications related both to lot and bid, but qualification status is not active - should return false.", () => {
            tender.qualifications[0].lotID = lot.id;
            tender.qualifications[0].status = "";
            assert.isFalse(bids.check_qualification_for_bid(tender, bid, lot));
        });

        it("tender has qualifications related both to bid and lot and qualification status is active - should return true.", () => {
            tender.qualifications[0].status = "active";
            assert.isTrue(bids.check_qualification_for_bid(tender, bid, lot));
        });
    });

    describe("check_qualification_for_EU_bid", () => {
        let bid, lot, tender, results;

        it("lot is in status unsuccessful - should return true (the results of check_qualification_for_bid and check_award_for_bid_multilot).", () => {
            bid = {
                bid: "bid_id"
            };
            lot = {
                lot: "lot_id",
                status: "unsuccessful"
            };
            tender = {
                qualifications: [{
                    bidID: bid.id,
                    lotID: lot.id,
                    status: "active"
                }]
            };

            assert.isTrue(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("tender status is active.pre-qualification, lot status is not unsuccessful and tender qualifications is all in status cancelled - should return false.", () => {
            lot.status = "";
            tender.status = "active.pre-qualification";
            tender.qualifications[0].status = "cancelled";
            tender.revisions = [];
            assert.isFalse(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("tender status is active.pre-qualification (couse of revisions), lot status is not unsuccessful and tender qualifications is all in status cancelled - should return false.", () => {
            lot.status = "";
            tender.status = "";
            tender.lots = [];
            tender.revisions.push(
                {
                    date: "2017-11-14T00:00:00Z",
                    changes: [
                        {
                            path: "/something",
                            op: "remove"
                        }
                    ]
                },
                {
                    date: "2017-11-14T00:00:00Z",
                    changes: [
                        {
                            path: "/status",
                            op: "add",
                            value: "active.pre-qualification"
                        }
                    ]
                }
            );

            assert.isFalse(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("tender status is active.pre-qualification.stand-still, lot status is not unsuccessful and tender has no qualifications in status active - should return false.", () => {
            lot.status = "";
            tender.status = "active.pre-qualification.stand-still";
            assert.isFalse(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });


        it("tender has cancelled lot and prev status was active.pre-qualification, and qualifications was not cancelled - should return true", () => {
            bid = {
                id: "bid_id"
            };
            lot = {
                id: "lot_id",
                status: "cancelled"
            };
            tender = {
                qualifications: [{
                    bidID: bid.id,
                    lotID: lot.id,
                    status: "cancelled"
                }],
                status: "active"
            };
            tender.lots = [lot];
            tender.bids = [bid];
            tender.revisions = [
                {
                    date: "2017-11-14T00:00:00Z",
                        changes: [
                            {
                                path: "/something",
                                op: "remove"
                            }
                        ]
                    },
                {
                    date: "2017-11-14T00:00:00Z",
                    changes: [
                        {
                            path: "/lots/0/status",
                            op: "replace",
                            value: "active"
                        },
                        {
                            path: "/status",
                            value: "active.pre-qualification",
                            op: "replace"
                        },
                        {
                            path: "/qualifications/0/status",
                            value: "not_cancelled",
                            op: "replace"
                        }
                    ]
                }
            ];
            assert.isTrue(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("tender has cancelled lot and prev status was active.pre-qualification.stand-still, and qualifications was active - should return true", () => {
            bid = {
                id: "bid_id"
            };
            lot = {
                id: "lot_id",
                status: "cancelled"
            };
            tender = {
                qualifications: [{
                    bidID: bid.id,
                    lotID: lot.id,
                    status: "cancelled"
                }],
                status: "active"
            };
            tender.lots = [lot];
            tender.bids = [bid];
            tender.revisions = [
                {
                    date: "2017-11-14T00:00:00Z",
                        changes: [
                            {
                                path: "/something",
                                op: "remove"
                            }
                        ]
                    },
                {
                    date: "2017-11-14T00:00:00Z",
                    changes: [
                        {
                            path: "/lots/0/status",
                            op: "replace",
                            value: "active"
                        },
                        {
                            path: "/status",
                            value: "active.pre-qualification.stand-still",
                            op: "replace"
                        },
                        {
                            path: "/qualifications/0/status",
                            value: "active",
                            op: "replace"
                        }
                    ]
                }
            ];
            assert.isTrue(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("tender has cancelled lot and prev status was active.pre-qualification.stand-still, and qualifications wasn't active - should return true", () => {
            bid = {
                id: "bid_id"
            };
            lot = {
                id: "lot_id",
                status: "cancelled"
            };
            tender = {
                qualifications: [{
                    bidID: bid.id,
                    lotID: lot.id,
                    status: "cancelled"
                }],
                status: "active"
            };
            tender.lots = [lot];
            tender.bids = [bid];
            tender.revisions = [
                {
                    date: "2017-11-14T00:00:00Z",
                        changes: [
                            {
                                path: "/something",
                                op: "remove"
                            }
                        ]
                    },
                {
                    date: "2017-11-14T00:00:00Z",
                    changes: [
                        {
                            path: "/lots/0/status",
                            op: "replace",
                            value: "active"
                        },
                        {
                            path: "/status",
                            value: "active.pre-qualification.stand-still",
                            op: "replace"
                        },
                        {
                            path: "/qualifications/0/status",
                            value: "unsuccessful",
                            op: "replace"
                        }
                    ]
                }
            ];
            assert.isFalse(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });


        it("no lot, no revisions, tender status is unsuccessful - should return true (the result of check_qualification_for_bid).", () => {
            lot = undefined;
            tender = {
                status: "unsuccessful",
                qualifications: [{
                    bidID: bid.id,
                    status: "active"
                }]
            };

            assert.isTrue(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("no lot, no revisions, tender status is unsuccessful and tender has awards - should return true (the results of check_award_for_bid and check_qualification_for_bid).", () => {
            tender.awards = [{
                bid_id: "not_bid_id"
            }];
            tender.qualifications = [{
                status: "active",
                bidID: bid.id
            }];

            assert.isTrue(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("no lot, revisions change tender status to active.pre-qualification, all qualifications have status cancelled - should return false.", () => {
            tender.revisions = [
                {
                    date: "2017-11-16T00:00:00Z",
                    changes: [
                        {
                            path: "/something",
                            op: "remove"
                        },
                        {
                            path: "/status",
                            op: "replace",
                            value: "active.pre-qualification"
                        }
                    ]
                }
            ]
            tender.qualifications[0].status = "cancelled";

            assert.isFalse(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("no lot, revisions change tender status to active.pre-qualification, tender has qualification not in status cancelled - should return true.", () => {
            tender.qualifications[0].status = "active";
            assert.isTrue(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("no lot, revisions change tender status to active.pre-qualification.stand-still, tender has qualification in status active - should return true.", () => {
            tender.revisions[0].changes[1].value = "active.pre-qualification.stand-still";
            tender.qualifications.push({status: "cancelled"});
            assert.isTrue(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });

        it("no lot, revisions change tender status to active.pre-qualification.stand-still, tender has no qualifications in status active - should return false.", () => {
            tender.qualifications[0].status = "cancelled";
            assert.isFalse(bids.check_qualification_for_EU_bid(tender, bid, lot));
        });
    });
});
